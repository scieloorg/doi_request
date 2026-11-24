import os
from io import BytesIO
from datetime import datetime
from datetime import timedelta
import functools

from celery import Celery
from celery import Task, chain
from celery.utils.log import get_task_logger
from lxml import etree
import requests
import xmlschema
from articlemeta.client import ThriftClient, ServerError
from crossref import relations
from crossref.client import (
    API_URL, DEPOSIT_URL, CrossrefClient, CrossrefLookupError)
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


class RelatedDocumentNotFound(Exception):
    pass


class RelationCycleError(Exception):
    pass


REQUEST_DOI_MAX_RETRY = int(os.environ.get('REQUEST_DOI_MAX_RETRY', '20000'))
REGISTER_DOI_MAX_RETRY = int(os.environ.get('REGISTER_DOI_MAX_RETRY', '20000'))
REQUEST_DOI_DELAY_RETRY = int(os.environ.get('REQUEST_DOI_DELAY_RETRY', '600'))
REGISTER_DOI_DELAY_RETRY = int(os.environ.get('REGISTER_DOI_DELAY_RETRY', '600'))
RELATIONS_MAX_RETRY = REQUEST_DOI_MAX_RETRY
RELATIONS_DELAY_RETRY = REQUEST_DOI_DELAY_RETRY
REQUEST_DOI_DELAY_RETRY_TD = timedelta(seconds=REQUEST_DOI_DELAY_RETRY)
REGISTER_DOI_DELAY_RETRY_TD = timedelta(seconds=REGISTER_DOI_DELAY_RETRY)
SUGGEST_DOI_IDENTIFICATION = asbool(os.environ.get('SUGGEST_DOI_IDENTIFICATION', False))
CROSSREF_SCHEMA_VERSION = os.environ.get('CROSSREF_SCHEMA_VERSION', '5.5.0')
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
CROSSREF_DEPOSIT_URL = os.environ.get('CROSSREF_DEPOSIT_URL') or DEPOSIT_URL
CROSSREF_API_URL = os.environ.get('CROSSREF_API_URL') or API_URL
ARTICLEMETA_THRIFTSERVER = os.environ.get(
    'ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621')

crossref_client = CrossrefClient(
    CROSSREF_PREFIX, CROSSREF_API_USER, CROSSREF_API_PASSWORD,
    deposit_url=CROSSREF_DEPOSIT_URL, api_url=CROSSREF_API_URL)


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
            'Required Crossref %s element not found: %s' % (
                CROSSREF_SCHEMA_VERSION, path
            )
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


def parse_xml(xml):
    return etree.parse(BytesIO(xml.encode('utf-8')))


def log_relation_event(session, code, title, status, body=''):
    log_event(session, {'title': title, 'body': body, 'type': 'relation', 'status': status, 'deposit_code': code})


def describe_relation(relation):
    return '%s --%s--> %s [%s]' % (
        relation.source_doi,
        relation.relationship_type,
        relation.target_doi,
        relation.element,
    )


def log_found_relations(session, deposit, found_relations):
    count = len(found_relations)
    log_relation_event(
        session, deposit.code,
        'Found %d related DOI relation%s in the document' % (
            count, '' if count == 1 else 's'),
        'info')
    for relation in found_relations:
        log_relation_event(
            session, deposit.code,
            'Relation found: %s' % describe_relation(relation),
            'info')


def check_targets_in_crossref(session, deposit, found_relations):
    """Consulta cada DOI alvo uma vez e mantém o resultado somente em memória."""
    registered_targets = {}
    for target_doi in sorted(set(
            relation.target_doi for relation in found_relations)):
        registered = crossref_client.is_doi_registered(target_doi)
        registered_targets[target_doi] = registered
        log_relation_event(
            session, deposit.code,
            'Related DOI %s is %s in Crossref' % (
                target_doi, 'registered' if registered else 'not registered'),
            'info')
    return registered_targets


def is_blocked_by(principal, dois):
    if principal.submission_status != 'blocked' or not principal.submission_xml:
        return False
    xml_doc = parse_xml(principal.submission_xml)
    principal_dois = set(relations.submission_dois(xml_doc))
    return any(
        relations.relation_role(relation, principal_dois) == relations.BLOCKING
        and relation.target_doi in dois
        for relation in relations.extract_doi_relations(xml_doc))


def block_deposit(session, deposit, own_dois, blocking_targets, articlemeta):
    """Bloqueia o depósito e localiza os depósitos principais de que depende.

    Retorna os PIDs dos principais que precisam ser enfileirados e a falha que
    impede o desbloqueio futuro, quando houver.
    """
    code = deposit.code
    now = datetime.now()
    deposit.submission_status = 'blocked'
    deposit.submission_updated_at = now
    deposit.updated_at = now
    log_title = 'Deposit blocked until related DOIs are registered in Crossref (%s)' % code
    logger.info(log_title)
    log_relation_event(session, code, log_title, 'info', '\n'.join(blocking_targets))

    principals_to_enqueue = []
    failure = None

    for target_doi in blocking_targets:
        principal = session.query(Deposit).filter_by(doi=target_doi).first()

        if principal is None:
            document = articlemeta.document(
                target_doi.upper(), deposit.collection_acronym)
            if document is None:
                failure = RelatedDocumentNotFound(
                    'Related DOI (%s) not found in ArticleMeta for (%s)' % (target_doi, code))
                break
            principals_to_enqueue.append(document.publisher_id)
            log_relation_event(
                session, code,
                'Principal document (%s) for related DOI (%s) enqueued for registration' % (
                    document.publisher_id, target_doi),
                'info')

        elif is_blocked_by(principal, own_dois):
            failure = RelationCycleError(
                'Deposits (%s) and (%s) are blocked waiting for each other' % (
                    code, principal.code))
            break

        else:
            log_relation_event(
                session, code,
                'Principal deposit (%s) for related DOI (%s) already exists' % (
                    principal.code, target_doi),
                'info',
                'submission status: %s, feedback status: %s' % (
                    principal.submission_status, principal.feedback_status))

    if failure is not None:
        deposit.submission_status = 'error'
        logger.error(str(failure))
        log_relation_event(session, code, str(failure), 'error')

    return principals_to_enqueue, failure


def unregistered_blocking_targets(found_relations, own_dois, registered_targets):
    """DOIs bloqueantes que ainda não estão registrados no Crossref."""
    targets = set()
    for relation in found_relations:
        role = relations.relation_role(relation, own_dois)
        target_doi = relation.target_doi
        is_blocking = role == relations.BLOCKING
        is_registered = registered_targets[target_doi]
        if is_blocking and not is_registered:
            targets.add(target_doi)
    return sorted(targets)


def unregistered_deferred_targets(found_relations, registered_targets):
    """DOIs alvo de relações que ainda não estão registrados no Crossref."""
    targets = set()
    for relation in found_relations:
        target_doi = relation.target_doi
        if not registered_targets[target_doi]:
            targets.add(target_doi)
    return targets


def strip_deferred_relations(session, deposit, xml_doc, deferred_targets):
    for relation in relations.strip_relations(xml_doc, deferred_targets):
        log_relation_event(
            session, deposit.code,
            'Relation deferred from the first submission: %s' %
            describe_relation(relation),
            'info')

    deposit.submission_xml = serialize_xml(xml_doc)
    deposit.updated_at = datetime.now()


def submission_chain():
    return [
        prepare_document.s().set(queue='dispatcher'),
        register_doi.s().set(queue='dispatcher'),
        request_doi_status.s().set(queue='releaser'),
    ]


@app.task(bind=True, max_retries=RELATIONS_MAX_RETRY,
          autoretry_for=(ServerError, CrossrefLookupError, requests.RequestException),
          throws=(RelatedDocumentNotFound, RelationCycleError))
@log_call
def resolve_relations(self, code):
    """Decide se o depósito pode seguir para o Crossref e o que vai no primeiro envio.

    Roda depois de ``load_xml_from_articlemeta`` e antes de ``prepare_document``.
    Lê as relações por DOI de ``submission_xml`` e consulta o Crossref. Todo
    estado das relações fica em variáveis locais e é recalculado nos retries.

    Há dois desfechos:

    - Algum alvo bloqueante ainda não está registrado (tradução, comentário,
      resposta, revisão, preprint ou errata). O depósito fica ``blocked``, os
      documentos principais sem depósito são enfileirados e esta tarefa tenta
      novamente até os DOIs aparecerem no Crossref.
    - Nenhum alvo bloqueante está pendente. As relações adiadas cujo DOI ainda
      não existe saem de ``submission_xml`` e a cadeia segue. O XML original
      será obtido novamente do ArticleMeta para o depósito final.

    ``CrossrefLookupError`` e falhas de rede são retentadas. ``ServerError`` do
    ArticleMeta também. ``RelatedDocumentNotFound`` e ``RelationCycleError``
    marcam o depósito como ``error`` e encerram a cadeia sem nova tentativa.

    Reprocessar não depende de estado persistido fora das colunas históricas.
    """
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)
    principals_to_enqueue = []
    failure = None

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()
        collection = deposit.collection_acronym
        xml_doc = parse_xml(deposit.submission_xml)
        own_dois = set(relations.submission_dois(xml_doc))
        found_relations = relations.extract_doi_relations(xml_doc)
        log_found_relations(session, deposit, found_relations)
        registered_targets = check_targets_in_crossref(
            session, deposit, found_relations)

        blocking_targets = unregistered_blocking_targets(
            found_relations, own_dois, registered_targets)

        if blocking_targets:
            principals_to_enqueue, failure = block_deposit(
                session, deposit, own_dois, blocking_targets, articlemeta)
        else:
            deposit.submission_status = 'waiting'
            deferref_targets = unregistered_deferred_targets(found_relations, registered_targets)
            strip_deferred_relations(session, deposit, xml_doc, deferref_targets)

    if failure is not None:
        raise failure

    if blocking_targets:
        for pid in principals_to_enqueue:
            registry_dispatcher_document_skip_deposited.delay(pid, collection)
        raise self.retry(
            exc=ChainAborted('Deposit blocked by related DOIs: %s' % code),
            countdown=RELATIONS_DELAY_RETRY)

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
            relations.set_batch_head(parsed_xml, datetime.utcnow())
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
    registered = False

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
                feedback_status, feedback_body = batch_feedback(xml_doc)
                log_title = 'Crossref final status for (%s) is (%s)' % (deposit.doi_batch_id, feedback_status)
                logger.info(log_title)
                now = datetime.now()
                deposit.feedback_status = feedback_status
                deposit.feedback_xml = etree.tostring(xml_doc).decode('utf-8')
                deposit.updated_at = now
                deposit.feedback_updated_at = now

                log_event(session, {'title': log_title, 'body': feedback_body, 'type': 'feedback', 'status': feedback_status, 'deposit_code': code})

                if feedback_status == 'success' and 'added' in feedback_body.lower():
                    register_expenses(session, deposit)

                registered = feedback_status == 'success'

    if exc_class:
        raise self.retry(exc=exc_class(exc_log_title))

    if registered:
        finalize_relations.apply_async(args=[code], queue='dispatcher')


def batch_feedback(xml_doc):
    """Resume o resultado de todos os registros do lote (um por DOI).

    O lote só é considerado ``success`` quando todos os registros são.
    """
    diagnostics = xml_doc.findall('.//record_diagnostic')
    if not diagnostics:
        raise ValueError('Crossref batch result without record_diagnostic')

    statuses = [diagnostic.get('status').lower() for diagnostic in diagnostics]
    failures = [status for status in statuses if status != 'success']
    body = '\n'.join(
        '%s: %s' % (diagnostic.findtext('doi'), diagnostic.findtext('msg'))
        for diagnostic in diagnostics)

    return (failures[0] if failures else 'success'), body


def register_expenses(session, deposit):
    if session.query(Expenses).filter_by(doi=deposit.doi).first() is not None:
        log_event(session, {'title': 'Expenses already registered for DOI (%s)' % deposit.doi, 'type': 'feedback', 'status': 'info', 'deposit_code': deposit.code})
        return

    #crossref backfiles limit current year - 2.
    back_file_limit = int(datetime.now().strftime('%Y')) - 2
    expenses = Expenses()
    expenses.publication_year = deposit.publication_year
    expenses.registry_date = datetime.now()
    expenses.doi = deposit.doi
    expenses.cost = 0.15 if int(deposit.publication_year) < back_file_limit else 1
    expenses.retro = True if int(deposit.publication_year) < back_file_limit else False
    session.add(expenses)


@app.task(bind=True, max_retries=RELATIONS_MAX_RETRY,
          autoretry_for=(ServerError, CrossrefLookupError, requests.RequestException),
          throws=(RelatedDocumentNotFound,))
@log_call
def finalize_relations(self, code):
    """Reavalia relações adiadas e prepara, uma única vez, o XML final.

    O XML original vem novamente do ArticleMeta. A diferença para o XML já
    submetido e a disponibilidade dos alvos no Crossref são recalculadas sem
    tabela ou coluna adicional.
    """
    articlemeta = ThriftClient(domain=ARTICLEMETA_THRIFTSERVER)
    retry_targets = []
    prepared = False

    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()
        if deposit.feedback_status != 'success':
            return code

        xml = articlemeta.document(
            deposit.pid, deposit.collection_acronym, fmt='xmlcrossref')
        if not xml:
            raise RelatedDocumentNotFound(
                'Crossref XML not found in ArticleMeta for (%s)' % deposit.code)
        original_doc = parse_xml(xml)
        submitted_doc = parse_xml(deposit.submission_xml)
        original_relations = set(relations.extract_doi_relations(original_doc))
        submitted_relations = set(relations.extract_doi_relations(submitted_doc))
        removed_relations = original_relations - submitted_relations

        if not removed_relations:
            return code

        registered_targets = check_targets_in_crossref(
            session, deposit, removed_relations)
        retry_targets = sorted(
            target for target, registered in registered_targets.items()
            if not registered)

        if not retry_targets:
            previous_batch_id = deposit.doi_batch_id
            now = datetime.now()
            updated = session.query(Deposit).filter_by(
                code=code,
                feedback_status='success',
                doi_batch_id=previous_batch_id,
            ).update({
                'submission_xml': serialize_xml(original_doc),
                'submission_status': 'waiting',
                'submission_updated_at': now,
                'feedback_status': 'waiting',
                'feedback_updated_at': now,
                'updated_at': now,
            }, synchronize_session=False)
            prepared = bool(updated)
            if prepared:
                log_relation_event(
                    session, code,
                    'Final submission with all relations prepared',
                    'info')

    if retry_targets:
        raise self.retry(
            exc=ChainAborted(
                'Final deposit waiting for related DOIs: %s' %
                ', '.join(retry_targets)),
            countdown=RELATIONS_DELAY_RETRY)

    if prepared:
        chain(*submission_chain()).delay(code)

    return code


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
        submission_xml='',
        submission_updated_at=now,
        submission_status='waiting',
        submission_response='',
        doi_batch_id=None,
        feedback_status=None,
        feedback_xml='',
        feedback_updated_at=None,
        is_xml_valid=False,
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
                session.flush()

        session.add(depitem)

    logger.info('deposit successfuly created for "%s": %s', code,
            repr(deposit))

    chain(
        triage_deposit.s(code).set(queue='dispatcher'),
        load_xml_from_articlemeta.s().set(queue='dispatcher'),
        resolve_relations.s().set(queue='dispatcher'),
        *submission_chain()
    ).delay()

