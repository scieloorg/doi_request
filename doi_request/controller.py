import os
import logging
import logging.config
from datetime import datetime
from io import BytesIO, StringIO

from lxml import etree

from articlemeta.client import ThriftClient
from tasks.celery import register_doi, request_doi_status
from doi_request.models.depositor import Deposit, LogEvent
from doi_request.models import DBSession

logger = logging.getLogger(__name__)

CROSSREF_XSD = open(os.path.dirname(__file__)+'/../xsd/crossref4.4.0.xsd')
CROSSREF_PREFIX = os.environ.get('CROSSREF_PREFIX', None)
CROSSREF_API_USER = os.environ.get('CROSSREF_API_USER', None)
CROSSREF_API_PASSWORD = os.environ.get('CROSSREF_API_PASSWORD', None)
CROSSREF_DEPOSITOR_NAME = os.environ.get('CROSSREF_DEPOSITOR_NAME', None)
CROSSREF_DEPOSITOR_EMAIL = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None)


class Depositor(object):

    def __init__(self, prefix=None, api_user=None, api_key=None, depositor_name=None, depositor_email=None, test_mode=False):

        self._articlemeta = ThriftClient(domain=os.environ.get('ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621'))
        self.prefix = prefix or CROSSREF_PREFIX
        self.api_user = api_user or CROSSREF_API_USER
        self.api_key = api_key or CROSSREF_API_PASSWORD
        self.depositor_name = depositor_name or CROSSREF_DEPOSITOR_NAME
        self.depositor_email = depositor_email or CROSSREF_DEPOSITOR_EMAIL
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

    def xml_is_valid(self, xml, only_front=False):
        xml = BytesIO(xml.encode('utf-8'))
        try:
            xml_doc = etree.parse(xml)
            logger.debug('XML is well formed')
        except Exception as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return (False, '', str(e))

        xml_doc = self._setup_depositor(xml_doc)

        if only_front:
            citation_list = xml_doc.find('//{http://www.crossref.org/schema/4.4.0}citation_list')
            if citation_list:
                citation_list.getparent().remove(citation_list)

        try:
            result = self.crossref_schema.assertValid(xml_doc)
            logger.debug('XML is valid')
            return (True, xml_doc, '')
        except etree.DocumentInvalid as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return (False, xml_doc, str(e))

    def deposit(self, document):

        code = '_'.join([document.collection_acronym, document.publisher_id])
        log_title = 'Reading document: %s' % code
        logger.info(log_title)
        xml_file_name = '%s.xml' % code
        doi_prefix = document.doi.split('/')[0] if document.doi else ''
        now = datetime.now()
        depitem = Deposit(
            code=code,
            pid=document.publisher_id,
            issn=document.journal.scielo_issn,
            volume=document.issue.volume,
            number=document.issue.number,
            issue_label=document.issue.label,
            journal=document.journal.title,
            journal_acronym=document.journal.acronym,
            collection_acronym=document.collection_acronym,
            xml_file_name=xml_file_name,
            doi=document.doi,
            prefix=doi_prefix,
            has_submission_xml_valid_references=False,
            submission_updated_at=now,
            submission_status='waiting',
            updated_at=now,
            started_at=now
        )

        deposit = DBSession.query(Deposit).filter_by(code=code).first()

        if deposit:
            DBSession.delete(deposit)
            DBSession.commit()

        deposit = DBSession.add(depitem)
        DBSession.commit()

        if not document.doi:
            now = datetime.now()
            log_title = 'Document DOI number not defined'
            depitem.submission_status = 'error'
            depitem.submission_updated_at = now
            depitem.updated_at = now
            logevent = LogEvent()
            logevent.title = log_title
            logevent.type = 'submission'
            logevent.status = 'error'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            DBSession.commit()
            return

        if doi_prefix.lower() != self.prefix.lower():
            now = datetime.now()
            log_title = 'Document DOI prefix (%s) do no match with the collection prefix (%s)' % (doi_prefix, self.prefix)
            depitem.submission_status = 'notapplicable'
            depitem.feedback_status = 'notapplicable'
            depitem.submission_updated_at = now
            depitem.feedback_updated_at = now
            depitem.updated_at = now
            logevent = LogEvent()
            logevent.title = log_title
            logevent.type = 'general'
            logevent.status = 'notapplicable'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            DBSession.commit()
            return

        try:
            log_title = 'Loading XML document from ArticleMeta (%s)' % code
            logevent = LogEvent()
            logevent.title = log_title
            logevent.type = 'submission'
            logevent.status = 'info'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            xml = self._articlemeta.document(document.publisher_id, document.collection_acronym, fmt='xmlcrossref')
        except Exception as exc:
            logger.exception(exc)
            now = datetime.now()
            log_title = 'Fail to load XML document from ArticleMeta (%s)' % code
            logger.error(log_title)
            depitem.submission_status = 'error'
            depitem.submission_updated_at = now
            depitem.updated_at = now
            logevent = LogEvent()
            logevent.title = log_title
            logevent.body = exc
            logevent.type = 'submission'
            logevent.status = 'error'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            return
        DBSession.commit()

        is_valid, parsed_xml, exc = self.xml_is_valid(xml)
        depitem.submission_xml = etree.tostring(parsed_xml, encoding='utf-8', pretty_print=True).decode('utf-8')

        if is_valid is True:
            log_title = 'XML is valid, it will be submitted to Crossref'
            now = datetime.now()
            logger.info(log_title)
            depitem.is_xml_valid = True
            depitem.has_submission_xml_valid_references = True
            depitem.submission_status = 'waiting'
            depitem.submission_updated_at = now
            depitem.doi_batch_id = parsed_xml.find('//{http://www.crossref.org/schema/4.4.0}doi_batch_id').text
            logevent = LogEvent()
            logevent.title = log_title
            logevent.type = 'submission'
            logevent.status = 'success'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            DBSession.commit()

            register_doi.apply_async(
                (code, depitem.submission_xml),
                link=request_doi_status.s(depitem.doi_batch_id)
            )
            return

        log_title = 'XML with references is invalid, fail to parse xml for document (%s)' % code
        now = datetime.now()
        logger.error(log_title)
        depitem.is_xml_valid = False
        depitem.submission_status = 'error'
        depitem.submission_updated_at = now
        depitem.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = exc
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = depitem.code
        DBSession.add(logevent)
        DBSession.commit()

        log_title = 'Trying to send XML without references'
        now = datetime.now()
        logger.error(log_title)
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'info'
        logevent.deposit_code = depitem.code
        DBSession.add(logevent)
        DBSession.commit()

        is_valid, parsed_xml, exc = self.xml_is_valid(xml, only_front=True)
        front_xml = etree.tostring(parsed_xml, encoding='utf-8', pretty_print=True).decode('utf-8')

        if is_valid is True:
            log_title = 'XML only with front metadata is valid, it will be submitted to Crossref'
            now = datetime.now()
            logger.info(log_title)
            depitem.is_xml_valid = True
            depitem.submission_status = 'waiting'
            depitem.submission_updated_at = now
            depitem.doi_batch_id = parsed_xml.find('//{http://www.crossref.org/schema/4.4.0}doi_batch_id').text
            logevent = LogEvent()
            logevent.title = log_title
            logevent.type = 'submission'
            logevent.status = 'success'
            logevent.deposit_code = depitem.code
            DBSession.add(logevent)
            DBSession.commit()

            register_doi.apply_async(
                (code, front_xml),
                link=request_doi_status.s(depitem.doi_batch_id)
            )
            return

        log_title = 'XML only with front metadata is also invalid, fail to parse xml for document (%s)' % code
        now = datetime.now()
        logger.error(log_title)
        depitem.is_xml_valid = False
        depitem.submission_status = 'error'
        depitem.submission_updated_at = now
        depitem.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = exc
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = depitem.code
        DBSession.add(logevent)
        DBSession.commit()
        return

    def deposit_by_pid(self, pid, collection):

        document = self._articlemeta.document(pid, collection)

        self.deposit(document)
