import os
import time
from io import BytesIO
from datetime import datetime

from celery import Celery
from celery.utils.log import get_task_logger
from lxml import etree

from crossref.client import CrossrefClient
from doi_request.models import DepositItem

logger = get_task_logger(__name__)

app = Celery('tasks', broker='amqp://guest@rabbitmq//')

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


@app.task(bind=True, default_retry_delay=3, retry_kwargs={'max_retries': 100})
def register_doi(self, code, xml):
    deposit_item = DepositItem.objects(pk=code)[0]
    attempts = 0

    try:
        result = crossref_client.register_doi(code, xml)
    except Exception as exc:
        logger.error('Fail to Connect to Crossref API, retrying to submit later (%s)' % code)
        raise self.retry(exc=ComunicationError(exc))

    if result.status_code != 200:
        logger.error('Fail to Connect to Crossref API, retrying to submit later (%s)' % code)
        msg = 'Received %d for (%s)' % (result.status_code, code)
        logger.error(msg)
        raise self.retry(exc=RequestError(msg))

    if result.status_code == 200 and 'SUCCESS' in result.text:
        deposit_item.submission_response = result.text
        deposit_item.submission_status_code = result.status_code
        deposit_item.submission_status = 'success'
        deposit_item.submission_updated_at = datetime.now()
        deposit_item.updated_at = datetime.now()
        deposit_item.save()
        logger.debug('Success registering DOI for (%s)' % code)
        return (True, code)

    deposit_item.submission_status = 'error'
    deposit_item.submission_status_code = result.status_code
    deposit_item.submission_response = result.text
    deposit_item.submission_updated_at = datetime.now()
    deposit_item.updated_at = datetime.now()
    deposit_item.save()
    return (False, code)

@app.task(bind=True, default_retry_delay=60, retry_kwargs={'max_retries': 200})
def request_doi_status(self, deposit, doi_batch_id):
    is_doi_register_submitted, code = deposit
    deposit_item = DepositItem.objects(pk=code)[0]

    if is_doi_register_submitted is False:
        return False

    deposit_item.feedback_status = 'waiting'
    deposit_item.feedback_updated_at = datetime.now()
    deposit_item.updated_at = datetime.now()
    deposit_item.save()

    try:
        result = crossref_client.request_doi_status_by_batch_id(doi_batch_id)
    except Exception as exc:
        logger.error('Fail to Connect to Crossref API, retrying to check submission status later (%s)' % doi_batch_id)
        logger.error('Received %d for (%s)' % (result.status_code, doi_batch_id))
        raise self.retry(exc=ComunicationError(exc))

    if result.status_code != 200:
        logger.error('Fail to Connect to Crossref API, retrying to check submission status later (%s)' % doi_batch_id)
        msg = 'Received %d for (%s)' % (result.status_code, doi_batch_id)
        logger.error(msg)
        raise self.retry(exc=RequestError(msg))

    xml = BytesIO(result.text.encode('utf-8'))
    xml_doc = etree.parse(xml)
    doi_batch_status = xml_doc.find('.').get('status')

    if doi_batch_status != 'completed':
        msg = 'Waiting Crossref to load it (%s)' % doi_batch_id
        logger.error(msg)
        raise self.retry(exc=UnkownSubmission(msg))

    feedback_status = xml_doc.find('.//record_diagnostic').get('status').lower() or 'unkown'
    deposit_item.feedback_status = feedback_status
    deposit_item.feedback_xml = etree.tostring(xml_doc).decode('utf-8')
    deposit_item.updated_at = datetime.now()
    deposit_item.feedback_updated_at = datetime.now()
    deposit_item.save()
