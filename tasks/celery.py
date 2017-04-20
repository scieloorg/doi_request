import os
import time
from io import BytesIO
from datetime import datetime
from datetime import timedelta

from celery import Celery
from celery.utils.log import get_task_logger
from lxml import etree

from crossref.client import CrossrefClient
from doi_request.models.depositor import Deposit, LogEvent
from doi_request.models import configure_session_engine, DBSession


logger = get_task_logger(__name__)

# Celery Config
app = Celery('tasks', broker='amqp://guest@rabbitmq//')

# Database Config
configure_session_engine()
 
crossref_client = CrossrefClient(
    os.environ.get('CROSSREF_PREFIX', ''),
    os.environ.get('CROSSREF_API_USER', ''),
    os.environ.get('CROSSREF_API_PASSWORD', '')
)


class CrossrefExceptions(Exception):
    pass


class ComunicationError(CrossrefExceptions):
    pass


class RequestError(ComunicationError):
    pass


class UnkownSubmission(CrossrefExceptions):
    pass


REGISTER_DOI_DELAY_RETRY = 60
REQUEST_DOI_DELAY_RETRY = 60
REGISTER_DOI_DELAY_RETRY_TD = timedelta(seconds=REGISTER_DOI_DELAY_RETRY)
REQUEST_DOI_DELAY_RETRY_TD = timedelta(seconds=REQUEST_DOI_DELAY_RETRY)


@app.task(bind=True, default_retry_delay=REGISTER_DOI_DELAY_RETRY, retry_kwargs={'max_retries': 100})
def register_doi(self, code, xml):
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
        result = crossref_client.register_doi(code, xml)
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
        return (True, code)

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
    return (False, code)

@app.task(bind=True, default_retry_delay=REQUEST_DOI_DELAY_RETRY, retry_kwargs={'max_retries': 200})
def request_doi_status(self, deposit, doi_batch_id):
    is_doi_register_submitted, code = deposit
    deposit = DBSession.query(Deposit).filter_by(code=code).first()

    if is_doi_register_submitted is False:
        return False

    log_title = 'Checking DOI registering Status for (%s)' % doi_batch_id
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
        result = crossref_client.request_doi_status_by_batch_id(doi_batch_id)
    except Exception as exc:
        log_title = 'Fail to Connect to Crossref API, retrying to check submission status at (%s) for (%s)' % (
            datetime.now()+REQUEST_DOI_DELAY_RETRY_TD, doi_batch_id
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
            now+REQUEST_DOI_DELAY_RETRY_TD, doi_batch_id
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
        log_title = 'Crossref has received the request, waiting Crossref to process it (%s)' % doi_batch_id
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
    log_title = 'Crossref final status for (%s) is (%s)' % (doi_batch_id, feedback_status)
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
