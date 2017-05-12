import os
import time
from io import BytesIO
import pickle
from datetime import datetime
from datetime import timedelta

from celery import Celery
from celery import Task, chain
from celery.utils.log import get_task_logger
from lxml import etree
from articlemeta.client import ThriftClient

from crossref.client import CrossrefClient
from doi_request.models.depositor import Deposit, LogEvent, Expenses
from doi_request.models import configure_session_engine, DBSession

from celery.contrib import rdb

logger = get_task_logger(__name__)

# Celery Config
app = Celery('tasks', broker='amqp://guest@rabbitmq//')

# Database Config
configure_session_engine()


class CrossrefExceptions(Exception):
    pass


class ComunicationError(CrossrefExceptions):
    pass


class RequestError(ComunicationError):
    pass


class UnkownSubmission(CrossrefExceptions):
    pass


class ChainAborted(Exception):
    pass

REGISTER_DOI_DELAY_RETRY = 600
REQUEST_DOI_DELAY_RETRY = 600
REGISTER_DOI_DELAY_RETRY_TD = timedelta(seconds=REGISTER_DOI_DELAY_RETRY)
REQUEST_DOI_DELAY_RETRY_TD = timedelta(seconds=REQUEST_DOI_DELAY_RETRY)
CROSSREF_XSD = open(os.path.dirname(__file__)+'/../xsd/crossref4.4.0.xsd')
CROSSREF_PREFIX = os.environ.get('CROSSREF_PREFIX', None)
CROSSREF_API_USER = os.environ.get('CROSSREF_API_USER', None)
CROSSREF_API_PASSWORD = os.environ.get('CROSSREF_API_PASSWORD', None)
CROSSREF_DEPOSITOR_NAME = os.environ.get('CROSSREF_DEPOSITOR_NAME', None)
CROSSREF_DEPOSITOR_EMAIL = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None)
ARTICLEMETA_THRIFTSERVER = os.environ.get(
    'ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621')

crossref_client = CrossrefClient(
    CROSSREF_PREFIX, CROSSREF_API_USER, CROSSREF_API_PASSWORD)


def _parse_schema():

    try:
        sch_doc = etree.parse(CROSSREF_XSD)
        sch = etree.XMLSchema(sch_doc)
    except Exception as e:
        logger.exception(e)
        logger.error('Fail to parse XML')
        return False

    return sch


PARSED_SCHEMA = _parse_schema()

@app.task(bind=True, max_retries=1)
def triage_deposit(self, code):

    deposit = DBSession.query(Deposit).filter_by(code=code).first()

    if not deposit.doi:
        now = datetime.now()
        log_title = 'Document DOI number not defined'
        deposit.submission_status = 'error'
        deposit.submission_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise ChainAborted(log_title)

    if deposit.prefix.lower() != CROSSREF_PREFIX.lower():
        now = datetime.now()
        log_title = 'Document DOI prefix (%s) do no match with the collection prefix (%s)' % (deposit.prefix, CROSSREF_PREFIX)
        deposit.submission_status = 'notapplicable'
        deposit.feedback_status = 'notapplicable'
        deposit.submission_updated_at = now
        deposit.feedback_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'general'
        logevent.status = 'notapplicable'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise ChainAborted(log_title)

    return code

@app.task(bind=True, default_retry_delay=60, max_retries=100)
def load_xml_from_articlemeta(self, code):

    deposit = DBSession.query(Deposit).filter_by(code=code).first()
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)

    try:
        log_title = 'Loading XML document from ArticleMeta (%s)' % code
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'info'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        xml = articlemeta.document(
            deposit.pid, deposit.collection_acronym, fmt='xmlcrossref'
        )
    except Exception as exc:
        logger.exception(exc)
        now = datetime.now()
        log_title = 'Fail to load XML document from ArticleMeta (%s)' % code
        logger.error(log_title)
        deposit.submission_status = 'error'
        deposit.submission_updated_at = datetime.now()
        deposit.updated_at = datetime.now()
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = exc
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=ComunicationError(log_title))

    log_title = 'XML Document loaded from ArticleMeta (%s)' % code
    deposit.submission_status = 'waiting'
    deposit.submission_xml = xml
    deposit.submission_updated_at = datetime.now()
    deposit.updated_at = datetime.now()
    logevent = LogEvent()
    logevent.title = log_title
    logevent.type = 'submission'
    logevent.status = 'success'
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()

    return code

@app.task(bind=True, default_retry_delay=REGISTER_DOI_DELAY_RETRY, max_retries=2000)
def prepare_document(self, code):

    def setup_depositor(xml):
        registrant = xml.find('//{http://www.crossref.org/schema/4.4.0}registrant')
        registrant.text = CROSSREF_DEPOSITOR_NAME
        depositor_name = xml.find('//{http://www.crossref.org/schema/4.4.0}depositor_name')
        depositor_name.text = CROSSREF_DEPOSITOR_NAME
        depositor_email = xml.find('//{http://www.crossref.org/schema/4.4.0}email_address')
        depositor_email.text = CROSSREF_DEPOSITOR_EMAIL

        return xml

    def xml_is_valid(xml, only_front=False):
        xml = BytesIO(xml.encode('utf-8'))
        try:
            xml_doc = etree.parse(xml)
            logger.debug('XML is well formed')
        except Exception as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return (False, '', str(e))

        xml_doc = setup_depositor(xml_doc)

        if only_front:
            citation_list = xml_doc.find(
                '//{http://www.crossref.org/schema/4.4.0}citation_list')
            if citation_list:
                citation_list.getparent().remove(citation_list)

        try:
            result = PARSED_SCHEMA.assertValid(xml_doc)
            logger.debug('XML is valid')
            return (True, xml_doc, '')
        except etree.DocumentInvalid as e:
            logger.exception(e)
            logger.error('Fail to parse XML')
            return (False, xml_doc, str(e))

    deposit = DBSession.query(Deposit).filter_by(code=code).first()
    is_valid, parsed_xml, exc = xml_is_valid(deposit.submission_xml)
    deposit.submission_xml = etree.tostring(parsed_xml, encoding='utf-8', pretty_print=True).decode('utf-8')

    if is_valid is True:
        log_title = 'XML is valid, it will be submitted to Crossref'
        now = datetime.now()
        logger.info(log_title)
        deposit.is_xml_valid = True
        deposit.has_submission_xml_valid_references = True
        deposit.submission_status = 'waiting'
        deposit.submission_updated_at = now
        deposit.doi_batch_id = parsed_xml.find(
            '//{http://www.crossref.org/schema/4.4.0}doi_batch_id').text
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'success'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        return code

    log_title = 'XML with references is invalid, fail to parse xml for document (%s)' % code
    now = datetime.now()
    logger.warning(log_title)
    deposit.is_xml_valid = False
    deposit.submission_status = 'error'
    deposit.submission_updated_at = now
    deposit.updated_at = now
    logevent = LogEvent()
    logevent.title = log_title
    logevent.body = exc
    logevent.type = 'submission'
    logevent.status = 'error'
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()

    log_title = 'Trying to send XML without references'
    now = datetime.now()
    logger.debug(log_title)
    logevent = LogEvent()
    logevent.title = log_title
    logevent.type = 'submission'
    logevent.status = 'info'
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()

    is_valid, parsed_xml, exc = xml_is_valid(
        deposit.submission_xml, only_front=True
    )
    deposit.submission_xml = etree.tostring(parsed_xml, encoding='utf-8', pretty_print=True).decode('utf-8')

    if is_valid is True:
        log_title = 'XML only with front metadata is valid, it will be submitted to Crossref'
        now = datetime.now()
        logger.info(log_title)
        deposit.is_xml_valid = True
        deposit.submission_status = 'waiting'
        deposit.submission_updated_at = now
        deposit.doi_batch_id = parsed_xml.find(
            '//{http://www.crossref.org/schema/4.4.0}doi_batch_id').text
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'success'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()

        return code

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
    raise ChainAborted(log_title)


@app.task(bind=True, default_retry_delay=REGISTER_DOI_DELAY_RETRY, max_retries=20000)
def register_doi(self, code):

    deposit = DBSession.query(Deposit).filter_by(code=code).first()

    try:
        log_title = 'Sending XML to Crossref'
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'submission'
        logevent.status = 'info'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        result = crossref_client.register_doi(code, deposit.submission_xml)
    except Exception as exc:
        log_title = 'Fail to Connect to Crossref API, retrying at (%s) to submit (%s)' % (
            datetime.now()+REGISTER_DOI_DELAY_RETRY_TD, code
        )
        logger.error(log_title)
        now = datetime.now()
        deposit.submission_status = 'waiting'
        deposit.submission_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = str(exc)
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=ComunicationError(log_title))

    if result.status_code != 200:
        log_title = 'Fail to Connect to Crossref API, retrying at (%s) to submit (%s)' % (
            datetime.now()+REGISTER_DOI_DELAY_RETRY_TD, code
        )
        logger.error(log_title)
        now = datetime.now()
        deposit.submission_log = log_title
        deposit.submission_status = 'waiting'
        deposit.submission_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = str('HTTP status code %d' % result.status_code)
        logevent.type = 'submission'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=RequestError(log_title))

    if result.status_code == 200 and 'SUCCESS' in result.text:
        log_title = 'Success sending metadata for (%s)' % code
        logger.debug(log_title)
        now = datetime.now()
        deposit.submission_status = 'success'
        deposit.submission_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = result.text
        logevent.type = 'submission'
        logevent.status = 'success'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        return code

    log_title = 'Fail registering DOI for (%s)' % code
    now = datetime.now()
    deposit.submission_status = 'error'
    deposit.submission_updated_at = now
    deposit.updated_at = now
    logevent = LogEvent()
    logevent.title = log_title
    logevent.body = result.text
    logevent.type = 'submission'
    logevent.status = 'error'
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()
    raise ChainAborted(log_title)


class CallbackTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        code = args[0]

        deposit = DBSession.query(Deposit).filter_by(code=code).first()

        log_title = 'Fail to registry DOI (%s) for (%s)' % (
            deposit.doi, deposit.doi_batch_id
        )
        logger.error(log_title)
        now = datetime.now()
        deposit.feedback_status = 'error'
        deposit.feedback_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'feedback'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()


@app.task(base=CallbackTask, bind=True, default_retry_delay=REQUEST_DOI_DELAY_RETRY, max_retries=20000)
def request_doi_status(self, code):

    deposit = DBSession.query(Deposit).filter_by(code=code).first()

    log_title = 'Checking DOI registering Status for (%s)' % deposit.doi_batch_id
    now = datetime.now()
    deposit.feedback_status = 'waiting'
    deposit.feedback_updated_at = now
    deposit.updated_at = now
    logevent = LogEvent()
    logevent.title = log_title
    logevent.type = 'feedback'
    logevent.status = 'info'
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()

    try:
        result = crossref_client.request_doi_status_by_batch_id(deposit.doi_batch_id)
    except Exception as exc:
        log_title = 'Fail to Connect to Crossref API, retrying to check submission status at (%s) for (%s)' % (
            datetime.now()+REQUEST_DOI_DELAY_RETRY_TD, deposit.doi_batch_id
        )
        logger.error(log_title)
        now = datetime.now()
        deposit.feedback_status = 'waiting'
        deposit.feedback_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'feedback'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=ComunicationError(log_title))

    deposit.feedback_request_status_code = result.status_code
    if result.status_code != 200:
        now = datetime.now()
        log_title = 'Fail to Connect to Crossref API, retrying to check submission status at (%s) (%s)' % (
            now+REQUEST_DOI_DELAY_RETRY_TD, deposit.doi_batch_id
        )
        deposit.feedback_status = 'waiting'
        deposit.feedback_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.body = str('HTTP status code %d' % result.status_code)
        logevent.type = 'feedback'
        logevent.status = 'error'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=RequestError(log_title))

    xml = BytesIO(result.text.encode('utf-8'))
    xml_doc = etree.parse(xml)
    doi_batch_status = xml_doc.find('.').get('status')
    if doi_batch_status != 'completed':
        log_title = 'Crossref has received the request, waiting Crossref to process it (%s)' % deposit.doi_batch_id
        logger.error(log_title)
        now = datetime.now()
        deposit.feedback_status = 'waiting'
        deposit.feedback_updated_at = now
        deposit.updated_at = now
        logevent = LogEvent()
        logevent.title = log_title
        logevent.type = 'feedback'
        logevent.status = 'info'
        logevent.deposit_code = deposit.code
        DBSession.add(logevent)
        DBSession.commit()
        raise self.retry(exc=UnkownSubmission(log_title))

    feedback_status = xml_doc.find('.//record_diagnostic').get('status').lower() or 'unkown'
    feedback_body = xml_doc.find('.//record_diagnostic/msg').text or ''
    log_title = 'Crossref final status for (%s) is (%s)' % (deposit.doi_batch_id, feedback_status)
    logger.info(log_title)
    now = datetime.now()
    deposit.feedback_status = feedback_status
    deposit.feedback_xml = etree.tostring(xml_doc).decode('utf-8')
    deposit.updated_at = now
    deposit.feedback_updated_at = now
    logevent = LogEvent()
    logevent.title = log_title
    logevent.body = feedback_body
    logevent.type = 'feedback'
    logevent.status = feedback_status
    logevent.deposit_code = deposit.code
    DBSession.add(logevent)
    DBSession.commit()

    if feedback_status == 'success' and 'added' in feedback_body.lower():
        #crossref backfiles limit current year - 2.
        back_file_limit = int(datetime.now().strftime('%Y')) - 2
        expenses = Expenses()
        expenses.publication_year = deposit.publication_year
        expenses.registry_date = datetime.now()
        expenses.doi = deposit.doi
        expenses.cost = 0.25 if int(deposit.publication_year) < back_file_limit else 1
        expenses.retro = True if int(deposit.publication_year) < back_file_limit else False
        DBSession.add(expenses)
        DBSession.commit()

@app.task(bind=True, max_retries=1)
def registry_dispatcher_document(self, code, collection):
    """
    This task receive a list of codes that should be queued for DOI registry
    """
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)
    document = articlemeta.document(code, collection)
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
        publication_year=int(document.publication_date[0:4]),
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

    chain(
        triage_deposit.s(code),
        load_xml_from_articlemeta.s(),
        prepare_document.s(),
        register_doi.s(),
        request_doi_status.s()
    ).apply_async()


@app.task(bind=True, max_retries=1)
def registry_dispatcher(self, pids_list):

    for item in pids_list:
        collection, code = item.split('_')

        registry_dispatcher_document.delay(code, collection)
