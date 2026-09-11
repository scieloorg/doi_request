import os
from io import BytesIO
from datetime import datetime
from datetime import timedelta
import functools

from celery import Celery
from celery import Task, chain
from celery.utils.log import get_task_logger
from lxml import etree
import xmlschema
from articlemeta.client import ThriftClient, ServerError

from crossref.client import CrossrefClient
from doi_request.models.depositor import Deposit, LogEvent, Expenses
from doi_request.models import transactional_session
from utils.settings import asbool


logger = get_task_logger(__name__)

# Celery Config
app = Celery('tasks', broker='redis://redis:6379/0')



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


REQUEST_DOI_MAX_RETRY = int(os.environ.get('REQUEST_DOI_MAX_RETRY', '20000'))
REGISTER_DOI_MAX_RETRY = int(os.environ.get('REGISTER_DOI_MAX_RETRY', '20000'))
REQUEST_DOI_DELAY_RETRY = int(os.environ.get('REQUEST_DOI_DELAY_RETRY', '600'))
REGISTER_DOI_DELAY_RETRY = int(os.environ.get('REGISTER_DOI_DELAY_RETRY', '600'))
REQUEST_DOI_DELAY_RETRY_TD = timedelta(seconds=REQUEST_DOI_DELAY_RETRY)
REGISTER_DOI_DELAY_RETRY_TD = timedelta(seconds=REGISTER_DOI_DELAY_RETRY)
SUGGEST_DOI_IDENTIFICATION = asbool(os.environ.get('SUGGEST_DOI_IDENTIFICATION', False))
CROSSREF_SCHEMA_VERSION = '5.5.0'
CROSSREF_SCHEMA_NAMESPACE = (
    'http://www.crossref.org/schema/%s' % CROSSREF_SCHEMA_VERSION
)
CROSSREF_XSD_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'xsd',
    'crossref%s.xsd' % CROSSREF_SCHEMA_VERSION
))
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
        return xmlschema.XMLSchema11(CROSSREF_XSD_PATH)
    except Exception:
        logger.exception(
            'Fail to parse Crossref schema at "%s"', CROSSREF_XSD_PATH
        )
        raise


PARSED_SCHEMA = _parse_schema()


def _crossref_tag(name):
    return '{%s}%s' % (CROSSREF_SCHEMA_NAMESPACE, name)


def _required_element(xml_doc, path):
    element = xml_doc.find(path)
    if element is None:
        raise ValueError(
            'Required Crossref 5.5.0 element not found: %s' % path
        )
    return element


def setup_depositor(xml_doc, doi, depositor_name=None, depositor_email=None):
    depositor_name = depositor_name or CROSSREF_DEPOSITOR_NAME
    depositor_email = depositor_email or CROSSREF_DEPOSITOR_EMAIL

    _required_element(
        xml_doc, './/' + _crossref_tag('registrant')
    ).text = depositor_name
    _required_element(
        xml_doc, './/' + _crossref_tag('depositor_name')
    ).text = depositor_name
    _required_element(
        xml_doc, './/' + _crossref_tag('email_address')
    ).text = depositor_email
    _required_element(
        xml_doc,
        './/%s/%s' % (_crossref_tag('doi_data'), _crossref_tag('doi'))
    ).text = doi

    return xml_doc


def get_doi_batch_id(xml_doc):
    return _required_element(
        xml_doc, './/' + _crossref_tag('doi_batch_id')
    ).text


def serialize_xml(xml_doc):
    return etree.tostring(
        xml_doc,
        encoding='utf-8',
        pretty_print=True,
        xml_declaration=True
    ).decode('utf-8')


def xml_is_valid(xml, doi, only_front=False, schema=None,
                 depositor_name=None, depositor_email=None):
    if isinstance(xml, str):
        xml = xml.encode('utf-8')

    try:
        xml_doc = etree.parse(BytesIO(xml))
        logger.debug('XML is well formed')
    except Exception as exc:
        logger.exception(exc)
        logger.error('Fail to parse XML')
        return (False, None, str(exc))

    try:
        setup_depositor(
            xml_doc,
            doi,
            depositor_name=depositor_name,
            depositor_email=depositor_email
        )
    except ValueError as exc:
        logger.error(str(exc))
        return (False, xml_doc, str(exc))

    if only_front:
        citation_list = xml_doc.find(
            './/' + _crossref_tag('citation_list')
        )
        if citation_list is not None:
            citation_list.getparent().remove(citation_list)

    xml_doc_pprint = etree.tostring(xml_doc, pretty_print=True)
    xml_doc = etree.parse(BytesIO(xml_doc_pprint))
    validation_schema = schema or PARSED_SCHEMA
    errors = list(validation_schema.iter_errors(
        xml_doc_pprint.decode('utf-8')
    ))

    if errors:
        error_message = '\n'.join(str(error) for error in errors)
        logger.error('Crossref XML is invalid: %s', error_message)
        return (False, xml_doc, error_message)

    logger.debug('XML is valid')
    return (True, xml_doc, '')


def log_call(f):
    @functools.wraps(f)
    def _f(*args):
        logger.info('started the `%s` stage for "%s"', f.__name__, args[1:])
        r = f(*args)
        logger.info('finished the `%s` stage for "%s"', f.__name__, args[1:])
        return r
    return _f 


def log_event(session, data):
    log = LogEvent(**data)
    session.add(log)


@app.task(bind=True, throws=(ChainAborted,))
@log_call
def triage_deposit(self, code):
    log_title = ''

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()

        if not deposit.doi:
            logger.info('cannot get DOI from deposit "%s" of code "%s"',
                    deposit.id, code)
            now = datetime.now()
            deposit.submission_status = 'error'
            deposit.submission_updated_at = now
            deposit.updated_at = now

            log_title = 'DOI number not defined for this document'
            log_event(session, {'title': log_title, 'type': 'submission', 'status': 'error', 'deposit_code': code})

        elif deposit.prefix.lower() != CROSSREF_PREFIX.lower():
            now = datetime.now()
            deposit.submission_status = 'notapplicable'
            deposit.feedback_status = 'notapplicable'
            deposit.submission_updated_at = now
            deposit.feedback_updated_at = now
            deposit.updated_at = now

            log_title = 'DOI prefix for this document (%s) does not match with the collection\'s (%s)' % (deposit.prefix, CROSSREF_PREFIX)
            log_event(session, {'title': log_title, 'type': 'general', 'status': 'notapplicable', 'deposit_code': code})

    if log_title:
        raise ChainAborted(log_title + ': ' + code)

    return code


@app.task(bind=True, max_retries=10, task_time_limit=60,
        autoretry_for=(ServerError,), retry_backoff=True)
@log_call
def load_xml_from_articlemeta(self, code):
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)

    exc_log_title = ''

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()

        log_title = 'Loading XML document from ArticleMeta (%s)' % code
        log_event(session, {'title': log_title, 'type': 'submission', 'status': 'info', 'deposit_code': code})

        try:
            xml = articlemeta.document(
                deposit.pid, deposit.collection_acronym, fmt='xmlcrossref'
            )
        except Exception as exc:
            logger.info('could not fetch Crossref XML for "%s": %s', code, str(exc))
            logger.exception(exc)

            deposit.submission_status = 'error'
            deposit.submission_updated_at = datetime.now()
            deposit.updated_at = datetime.now()

            log_title = 'Fail to load XML document from ArticleMeta (%s)' % code
            log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})

            exc_log_title = log_title

        else:
            deposit.submission_status = 'waiting'
            deposit.submission_xml = xml
            deposit.submission_updated_at = datetime.now()
            deposit.updated_at = datetime.now()

            log_title = 'XML Document loaded from ArticleMeta (%s)' % code
            log_event(session, {'title': log_title, 'type': 'submission', 'status': 'success', 'deposit_code': code})

    if exc_log_title:
        raise self.retry(exc=ComunicationError(exc_log_title))

    return code


@app.task(bind=True, throws=(ChainAborted,))
@log_call
def prepare_document(self, code):
    """Modifica o XML que será enviado para o Crossref com dados do depositante.

    Os únicos tipos de erros passíveis de novas tentativas são os de comunicação
    com o banco de dados.
    """
    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()

        is_valid, parsed_xml, exc = xml_is_valid(
            deposit.submission_xml, deposit.doi
        )
        if parsed_xml is not None:
            deposit.submission_xml = serialize_xml(parsed_xml)

        if is_valid is True:
            log_title = 'XML is valid, it will be submitted to Crossref'
            now = datetime.now()
            logger.info(log_title)
            deposit.is_xml_valid = True
            deposit.has_submission_xml_valid_references = True
            deposit.submission_status = 'waiting'
            deposit.submission_updated_at = now
            deposit.doi_batch_id = get_doi_batch_id(parsed_xml)

            log_event(session, {'title': log_title, 'type': 'submission', 'status': 'success', 'deposit_code': code})
            return code

        log_title = 'XML with references is invalid, fail to parse xml for document (%s)' % code
        now = datetime.now()
        logger.warning(log_title)
        deposit.is_xml_valid = False
        deposit.submission_status = 'error'
        deposit.submission_updated_at = now
        deposit.updated_at = now

        log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})

        if parsed_xml is None:
            log_title = 'XML is not well formed for document (%s)' % code
            log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})
        else:
            log_title = 'Trying to send XML without references'
            logger.debug(log_title)
            log_event(session, {'title': log_title, 'type': 'submission', 'status': 'info', 'deposit_code': code})

            is_valid, parsed_xml, exc = xml_is_valid(
                deposit.submission_xml, deposit.doi, only_front=True
            )
            if parsed_xml is not None:
                deposit.submission_xml = serialize_xml(parsed_xml)

        if parsed_xml is not None and is_valid is True:
            log_title = 'XML only with front metadata is valid, it will be submitted to Crossref'
            now = datetime.now()
            logger.info(log_title)
            deposit.is_xml_valid = True
            deposit.submission_status = 'waiting'
            deposit.submission_updated_at = now
            deposit.doi_batch_id = get_doi_batch_id(parsed_xml)

            log_event(session, {'title': log_title, 'type': 'submission', 'status': 'success', 'deposit_code': code})

            return code

        log_title = 'XML only with front metadata is also invalid, fail to parse xml for document (%s)' % code
        now = datetime.now()
        logger.error(log_title)
        deposit.is_xml_valid = False
        deposit.submission_status = 'error'
        deposit.submission_updated_at = now
        deposit.updated_at = now

        log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})

    raise ChainAborted(log_title)


@app.task(bind=True, default_retry_delay=REGISTER_DOI_DELAY_RETRY, 
        max_retries=REGISTER_DOI_MAX_RETRY, throws=(ChainAborted,))
@log_call
def register_doi(self, code):
    should_abort_chain, exc_class, exc_log_title = (False, None, '')

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()

        log_title = 'Sending XML to Crossref'
        log_event(session, {'title': log_title, 'type': 'submission', 'status': 'info', 'deposit_code': code})

        try:
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

            log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})
            exc_class, exc_log_title = (ComunicationError, log_title)
        else:

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

                log_event(session, {'title': log_title, 'body': 'HTTP status code %d' % result.status_code, 'type': 'submission', 'status': 'error', 'deposit_code': code})
                exc_class, exc_log_title = (RequestError, log_title)

            elif result.status_code == 200 and 'SUCCESS' in result.text:
                log_title = 'Success sending metadata for (%s)' % code
                logger.debug(log_title)
                now = datetime.now()
                deposit.submission_status = 'success'
                deposit.submission_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'body': result.text, 'type': 'submission', 'status': 'success', 'deposit_code': code})
                return code

            else:
                log_title = 'Fail registering DOI for (%s)' % code
                now = datetime.now()
                deposit.submission_status = 'error'
                deposit.submission_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'body': result.text, 'type': 'submission', 'status': 'error', 'deposit_code': code})
                should_abort_chain, exc_log_title = (True, log_title)

    if should_abort_chain:
        raise ChainAborted(exc_log_title)
    else:
        raise self.retry(exc=exc_class(exc_log_title))


class CallbackTask(Task):

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        code = args[0]

        with transactional_session() as session:
            deposit = session.query(Deposit).filter_by(code=code).first()

            log_title = 'Fail to registry DOI (%s) for (%s)' % (
                deposit.doi, deposit.doi_batch_id
            )
            logger.error(log_title)
            now = datetime.now()
            deposit.feedback_status = 'error'
            deposit.feedback_updated_at = now
            deposit.updated_at = now

            log_event(session, {'title': log_title, 'type': 'feedback', 'status': 'error', 'deposit_code': code})


@app.task(base=CallbackTask, bind=True, default_retry_delay=REQUEST_DOI_DELAY_RETRY, max_retries=REQUEST_DOI_MAX_RETRY)
@log_call
def request_doi_status(self, code):
    exc_class, exc_log_title = (None, '')

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()

        log_title = 'Checking DOI registering Status for (%s)' % deposit.doi_batch_id
        now = datetime.now()
        deposit.feedback_status = 'waiting'
        deposit.feedback_updated_at = now
        deposit.updated_at = now

        log_event(session, {'title': log_title, 'type': 'feedback', 'status': 'info', 'deposit_code': code})

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

            log_event(session, {'title': log_title, 'body': str(exc), 'type': 'feedback', 'status': 'error', 'deposit_code': code})
            exc_class, exc_log_title = (ComunicationError, log_title)

        else:
            deposit.feedback_request_status_code = result.status_code
            xml = BytesIO(result.text.encode('utf-8'))
            xml_doc = etree.parse(xml)
            doi_batch_status = xml_doc.find('.').get('status')

            if result.status_code != 200:
                now = datetime.now()
                log_title = 'Fail to Connect to Crossref API, retrying to check submission status at (%s) (%s)' % (
                    now+REQUEST_DOI_DELAY_RETRY_TD, deposit.doi_batch_id
                )
                deposit.feedback_status = 'waiting'
                deposit.feedback_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'body': 'HTTP status code %d' % result.status_code, 'type': 'feedback', 'status': 'error', 'deposit_code': code})
                exc_class, exc_log_title = (RequestError, log_title)

            elif doi_batch_status != 'completed':
                log_title = 'Crossref has received the request, waiting Crossref to process it (%s)' % deposit.doi_batch_id
                logger.error(log_title)
                now = datetime.now()
                deposit.feedback_status = 'waiting'
                deposit.feedback_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'type': 'feedback', 'status': 'info', 'deposit_code': code})
                exc_class, exc_log_title = (UnkownSubmission, log_title)

            else:
                feedback_status = xml_doc.find('.//record_diagnostic').get('status').lower() or 'unkown'
                feedback_body = xml_doc.find('.//record_diagnostic/msg').text or ''
                log_title = 'Crossref final status for (%s) is (%s)' % (deposit.doi_batch_id, feedback_status)
                logger.info(log_title)
                now = datetime.now()
                deposit.feedback_status = feedback_status
                deposit.feedback_xml = etree.tostring(xml_doc).decode('utf-8')
                deposit.updated_at = now
                deposit.feedback_updated_at = now

                log_event(session, {'title': log_title, 'body': feedback_body, 'type': 'feedback', 'status': feedback_status, 'deposit_code': code})

                if feedback_status == 'success' and 'added' in feedback_body.lower():
                    #crossref backfiles limit current year - 2.
                    back_file_limit = int(datetime.now().strftime('%Y')) - 2
                    expenses = Expenses()
                    expenses.publication_year = deposit.publication_year
                    expenses.registry_date = datetime.now()
                    expenses.doi = deposit.doi
                    expenses.cost = 0.15 if int(deposit.publication_year) < back_file_limit else 1
                    expenses.retro = True if int(deposit.publication_year) < back_file_limit else False
                    session.add(expenses)

    if exc_class:
        raise self.retry(exc=exc_class(exc_log_title))


@app.task(bind=True, throws=(ChainAborted,), task_time_limit=60, 
        autoretry_for=(ServerError,), retry_backoff=True)
@log_call
def registry_dispatcher_document(self, code, collection):
    """
    This task receive a list of codes that should be queued for DOI registry
    """
    return _registry_dispatcher_document(code, collection, skip_deposited=False)


@app.task(bind=True, throws=(ChainAborted,), task_time_limit=60, 
        autoretry_for=(ServerError,), retry_backoff=True)
@log_call
def registry_dispatcher_document_skip_deposited(self, code, collection):
    """
    This task receive a list of codes that should be queued for DOI registry
    """
    return _registry_dispatcher_document(code, collection, skip_deposited=True)


def _registry_dispatcher_document(code, collection, skip_deposited):
    """
    This task receive a list of codes that should be queued for DOI registry
    """
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)
    document = articlemeta.document(code, collection)

    code = '_'.join([document.collection_acronym, document.publisher_id])
    log_title = 'Reading document: %s' % code
    logger.info(log_title)
    xml_file_name = '%s.xml' % code
    doi = document.doi or ''
    doi_prefix = document.doi.split('/')[0] if doi else ''
    now = datetime.now()

    if SUGGEST_DOI_IDENTIFICATION is True and not doi:
        doi_prefix = CROSSREF_PREFIX
        doi = '/'.join([CROSSREF_PREFIX, document.publisher_ahead_id or document.publisher_id])

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
        doi=doi,
        publication_year=int(document.publication_date[0:4]),
        prefix=doi_prefix,
        has_submission_xml_valid_references=False,
        submission_updated_at=now,
        submission_status='waiting',
        updated_at=now,
        started_at=now
    )

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()
        if deposit:
            if skip_deposited:
                logger.info('deposit already exists. skipping: "%s"', code)
                return
            else:
                logger.info('deposit already exists. it will be deleted and '
                            're-created: "%s"', code)
                session.delete(deposit)
        
        session.add(depitem)

    logger.info('deposit successfuly created for "%s": %s', code,
            repr(deposit))

    chain(
        triage_deposit.s(code).set(queue='dispatcher'),
        load_xml_from_articlemeta.s().set(queue='dispatcher'),
        prepare_document.s().set(queue='dispatcher'),
        register_doi.s().set(queue='dispatcher'),
        request_doi_status.s().set(queue='releaser')
    ).delay()

