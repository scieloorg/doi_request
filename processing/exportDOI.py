# coding: utf-8
"""
Este processamento realiza a exportação de registros SciELO para o Crossref
"""
import os
import argparse
import logging
import logging.config
import codecs
import json
from io import BytesIO, StringIO
from datetime import datetime, timedelta

from lxml import etree
import requests

from doi_request.models import DepositItem
from articlemeta.client import ThriftClient
from tasks.celery import register_doi, request_doi_status
from crossref.client import CrossrefClient

import utils

FROM = datetime.now() - timedelta(days=30)
FROM = FROM.isoformat()[:10]

CROSSREF_XSD = open(os.path.dirname(__file__)+'/../xsd/crossref4.4.0.xsd')
logger = logging.getLogger(__name__)

SENTRY_HANDLER = os.environ.get('SENTRY_HANDLER', None)
LOGGING_LEVEL = os.environ.get('LOGGING_LEVEL', 'DEBUG')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'console': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%H:%M:%S',
            },
        },
    'handlers': {
        'console': {
            'level': LOGGING_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'console'
            }
        },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': LOGGING_LEVEL,
            'propagate': False,
            },
        'processing.exportDOI': {
            'level': LOGGING_LEVEL,
            'propagate': True,
        },
    }
}

if SENTRY_HANDLER:
    LOGGING['handlers']['sentry'] = {
        'level': 'ERROR',
        'class': 'raven.handlers.logging.SentryHandler',
        'dsn': SENTRY_HANDLER,
    }
    LOGGING['loggers']['']['handlers'].append('sentry')


class ExportDOI(object):

    def __init__(self, collection, issns=None, output_file=None, from_date=FROM,
                 prefix=None, api_user=None, api_key=None, depositor_name=None,
                 depositor_email=None, test_mode=False):

        self._articlemeta = ThriftClient(domain=os.environ.get('ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621'))
        self.collection = collection
        self.from_date = from_date
        self.prefix = prefix
        self.api_user = api_user
        self.api_key = api_key
        self.depositor_name = depositor_name
        self.depositor_email = depositor_email
        self.issns = issns or [None]
        self.test_mode = test_mode
        self._parse_schema()

    def _parse_schema(self):

        try:
            sch_doc = etree.parse(CROSSREF_XSD)
            sch = etree.XMLSchema(sch_doc)
        except Exception as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return False

        self.crossref_schema = sch

    def _setup_depositor(self, xml):

        if self.depositor_name:
            registrant = xml.find('//{http://www.crossref.org/schema/4.4.0}registrant')
            registrant.text = self.depositor_name

            depositor_name = xml.find('//{http://www.crossref.org/schema/4.4.0}depositor_name')
            depositor_name.text = self.depositor_name

        if self.depositor_email:
            depositor_email = xml.find('//{http://www.crossref.org/schema/4.4.0}email_address')
            depositor_email.text = self.depositor_email

        return xml

    def xml_is_valid(self, xml):

        try:
            xml = BytesIO(xml.encode('utf-8'))
            xml_doc = etree.parse(xml)
            xml_doc = self._setup_depositor(xml_doc)
            logger.debug('XML is well formed')
        except Exception as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return False

        try:
            result = self.crossref_schema.assertValid(xml_doc)
            logger.debug('XML is valid')
            return xml_doc
        except Exception as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return False

    def deposit(self, document):

        code = '_'.join([document.collection_acronym, document.publisher_id])
        msg = 'Reading document: %s' % code
        logger.info(msg)
        xml_file_name = '%s.xml' % code
        doi_prefix = document.doi.split('/')[0] if document.doi else ''
        now = datetime.now()
        depitem = DepositItem(
            code=code,
            pid=document.publisher_id,
            collection_acronym=document.collection_acronym,
            xml_file_name=xml_file_name,
            doi=document.doi,
            prefix=doi_prefix,
            submission_updated_at=now,
            submission_status='waiting',
            submission_log=msg,
            updated_at=now,
            started_at=now
        )
        depitem.save()

        if doi_prefix.lower() != self.prefix.lower():
            now = datetime.now()
            msg = 'Document DOI prefix (%s) do no match with the collection prefix (%s)' % (doi_prefix, self.prefix)
            depitem.submission_status = 'notapplicable'
            depitem.submission_log = msg
            depitem.feedback_status = 'notapplicable'
            depitem.feddback_log = msg
            depitem.submission_updated_at = now
            depitem.feedback_updated_at = now
            depitem.updated_at = now
            depitem.save()
            return

        try:
            xml = self._articlemeta.document(document.publisher_id, document.collection_acronym, fmt='xmlcrossref')
        except Exception as exc:
            logger.exception(exc)
            now = datetime.now()
            msg = 'Fail to read document:  %s' % code
            logger.error(msg)
            depitem.xml_is_valid = False
            depitem.submission_log = msg
            depitem.submission_status = 'fail'
            depitem.submission_updated_at = now
            depitem.updated_at = now
            depitem.save()
            xml = ''
            return

        parsed_xml = self.xml_is_valid(xml)
        depitem.deposit_xml = etree.tostring(parsed_xml).decode('utf-8')

        if parsed_xml is False:
            msg = 'XML is invalid, fail to parse xml for document (%s)' % code
            now = datetime.now()
            logger.error(msg)
            depitem.xml_is_valid = False
            depitem.submission_log = msg
            depitem.submission_status = 'fail'
            depitem.submission_updated_at = now
            depitem.updated_at = now
            depitem.save()
            xml = ''
            return

        msg = 'XML is valid, it will be submitted to Crossref'
        now = datetime.now()
        logger.info(msg)
        depitem.xml_is_valid = True
        depitem.submission_status = 'waiting'
        doi_batch_id = parsed_xml.find('//{http://www.crossref.org/schema/4.4.0}doi_batch_id').text
        depitem.doi_batch_id = doi_batch_id
        depitem.submission_log = msg
        depitem.submission_updated_at = now
        depitem.updated_at = now
        depitem.save()

        register_doi.apply_async(
            (code, xml),
            link=request_doi_status.s(doi_batch_id)
        )

    def run(self):

        crossref_client = CrossrefClient(self.prefix, self.api_user, self.api_key, self.test_mode)
        count = 0
        for issn in self.issns:
            for document in self._articlemeta.documents(
                    collection=self.collection, issn=issn,
                    from_date=self.from_date):

                count += 1
                if count >= 30:
                    break

                self.deposit(document)


def main():

    parser = argparse.ArgumentParser(
        description='Load documents into DOAJ'
    )

    parser.add_argument(
        'issns',
        nargs='*',
        help='ISSN\'s separated by spaces'
    )

    parser.add_argument(
        '--issns_file',
        '-i',
        default=None,
        help='Full path to a txt file within a list of ISSNs to be exported'
    )

    parser.add_argument(
        '--api_user',
        '-u',
        default=os.environ.get('CROSSREF_API_USER', None),
        help='Crossref Publisher account name'
    )

    parser.add_argument(
        '--api_key',
        '-p',
        default=os.environ.get('CROSSREF_API_PASSWORD', None),
        help='Crossref Publisher account password'
    )

    parser.add_argument(
        '--prefix',
        '-x',
        default=os.environ.get('CROSSREF_PREFIX', None),
        help='Crossref Prefix'
    )

    parser.add_argument(
        '--depositor_name',
        '-d',
        default=os.environ.get('CROSSREF_DEPOSITOR_NAME', None),
        help='Name of the depositor. It will be attached to the XML metadata'
    )

    parser.add_argument(
        '--depositor_email',
        '-e',
        default=os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None),
        help='Email of the depositor. It will be attached to the XML metadata'
    )

    parser.add_argument(
        '--test_mode',
        '-t',
        action='store_true',
        help='Set submission mode to Test Mode. It will use the Crossref Testing API '
    )

    parser.add_argument(
        '--collection',
        '-c',
        help='Collection Acronym'
    )

    parser.add_argument(
        '--from_date',
        '-f',
        default=FROM,
        help='ISO date like %s' % FROM
    )

    parser.add_argument(
        '--logging_level',
        '-l',
        default=LOGGING_LEVEL,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )

    args = parser.parse_args()
    LOGGING['handlers']['console']['level'] = args.logging_level
    for content in LOGGING['loggers'].values():
        content['level'] = args.logging_level
    logging.config.dictConfig(LOGGING)

    logger.info('Dumping data for: %s' % args.collection)

    issns = None
    if len(args.issns) > 0:
        issns = utils.ckeck_given_issns(args.issns)

    issns_from_file = None
    if args.issns_file:
        with open(args.issns_file, 'r') as f:
            issns_from_file = utils.ckeck_given_issns([i.strip() for i in f])

    if issns:
        issns += issns_from_file if issns_from_file else []
    else:
        issns = issns_from_file if issns_from_file else []

    export = ExportDOI(
        args.collection, issns, from_date=args.from_date, prefix=args.prefix,
        api_user=args.api_user, api_key=args.api_key,
        depositor_name=args.depositor_name, depositor_email=args.depositor_email,
        test_mode=args.test_mode)

    export.run()
