# coding: utf-8
"""
Este processamento realiza a exportação de uma listagem de DOI's registrados no
crossref para o formato ID do ISIS para fins de compativilidade com a interface
do site SciELO que utiliza uma base de dados ISIS para a apresentação dos números
DOI em sua interface.

O resultado deste processamento é um arquivo no formato ID com a listagem completa
de DOI's e PIDS de uma determinada coleção.

!ID 1
!v880!S0102-86502002000900005
!v001!10.1590/S0102-86502002000900005
!v237!10.1590/S0102-86502002000900005
!v003!art
!ID 2
!v880!S0102-8650200200090000500001
!v001!10.1097/00000478-199812000-00001
!v237!10.1097/00000478-199812000-00001
"""
import os
from io import BytesIO
import argparse
import logging
import logging.config

from lxml import etree

from doi_request.models.depositor import Deposit, LogEvent, Expenses
from doi_request.models import configure_session_engine, DBSession

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
        'processing.export2id': {
            'level': LOGGING_LEVEL,
            'propagate': True,
        },
        'doi_request': {
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

# Database Config
configure_session_engine()


class Export2Id(object):

    def __init__(self, output_file):

        self.output_file = open(output_file, 'w', encoding='utf-8') if output_file else output_file

    def extract_ref_dois(self, xml):

        xml = BytesIO(xml.encode('utf-8'))
        try:
            xml_doc = etree.parse(xml)
            logger.debug('XML is well formed')
        except Exception as e:
            import pdb; pdb.set_trace()
            logger.exception(e)
            logger.error('Fail to parse XML')
            return []

        citations = xml_doc.findall("./record_diagnostic/citations_diagnostic/citation[@status='resolved_reference']")

        for citation in citations:
            ref_number = int(citation.get('key')[3:])
            yield ("%05d" % ref_number, citation.text)

    def write(self, line):

        if not self.output_file:
            print(line.encode('utf-8'))
        else:
            self.output_file.write('%s\r\n' % line)

    def run(self):
        logger.info("Processing started")
        deposits = DBSession.query(Deposit)
        ndx = 0

        for deposit in deposits:
            logger.debug("Reading registry (%s)", deposit.code)
            if not deposit.doi:
                continue
            ndx += 1
            self.write('!ID %s' % str(ndx))
            self.write('!v880!%s' % deposit.pid)
            self.write('!v001!%s' % deposit.doi)
            self.write('!v237!%s' % deposit.doi)
            self.write('!v003!%s' % 'art')

            if not deposit.feedback_xml:
                logger.debug('Crossref reponse XML not available, skiping references DOI checking')
                continue

            for reference in self.extract_ref_dois(deposit.feedback_xml):
                if not reference:
                    continue
                ndx += 1
                self.write('!ID %s' % str(ndx))
                self.write('!v880!%s' % deposit.pid+reference[0])
                self.write('!v001!%s' % reference[1])
                self.write('!v003!%s' % 'ref')
                self.write('!v237!%s' % reference[1])

        logger.info("Processing finished")


def main():

    parser = argparse.ArgumentParser(
        description='Produce a list of DOIs X PIDs in ISIS ID format'
    )

    parser.add_argument(
        '--output_file',
        '-o',
        help='Output file name. Stdout is default.'
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

    export = Export2Id(args.output_file)

    export.run()
