from io import BytesIO
from datetime import datetime

from celery import Celery
from celery import Task, chain
from celery.utils.log import get_task_logger
from lxml import etree
import requests
from articlemeta.client import ThriftClient, ServerError
from crossref import relations
from crossref.client import CrossrefLookupError
from doi_request.models.depositor import Deposit
from doi_request.models import transactional_session
from tasks.dispatch import registry_dispatcher_document as enqueue_document
from tasks.exceptions import (
    ChainAborted,
    ComunicationError,
    RelatedDocumentNotFound,
    RequestError,
    UnkownSubmission,
)
from tasks.expenses import register_expenses
from tasks.feedback import batch_feedback
from tasks.logging import log_call, log_event, log_found_relations, log_relation_event
from tasks.relations import (
    block_deposit,
    check_targets_in_crossref,
    strip_deferred_relations,
    unregistered_blocking_targets,
    unregistered_deferred_targets,
)
from tasks.settings import (
    ARTICLEMETA_THRIFTSERVER,
    CROSSREF_PREFIX,
    REGISTER_DOI_DELAY_RETRY,
    REGISTER_DOI_DELAY_RETRY_TD,
    REGISTER_DOI_MAX_RETRY,
    RELATIONS_DELAY_RETRY,
    RELATIONS_MAX_RETRY,
    REQUEST_DOI_DELAY_RETRY,
    REQUEST_DOI_DELAY_RETRY_TD,
    REQUEST_DOI_MAX_RETRY,
    crossref_client,
)
from tasks.xml import get_doi_batch_id, parse_xml, serialize_xml, xml_is_valid


logger = get_task_logger(__name__)

app = Celery('tasks', broker='redis://redis:6379/0')


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


def submission_chain():
    return [
        prepare_document.s().set(queue='dispatcher'),
        register_doi.s().set(queue='dispatcher'),
        request_doi_status.s().set(queue='releaser'),
    ]


@app.task(bind=True, max_retries=RELATIONS_MAX_RETRY,
          autoretry_for=(ServerError, CrossrefLookupError, requests.RequestException),
          throws=(RelatedDocumentNotFound,))
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
    ArticleMeta também. ``RelatedDocumentNotFound`` marca o depósito como
    ``error`` e encerra a cadeia sem nova tentativa.

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
                session, deposit, blocking_targets, articlemeta)
        else:
            deferred_targets = unregistered_deferred_targets(
                found_relations, registered_targets)
            strip_deferred_relations(
                session, deposit, xml_doc, deferred_targets)

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

        log_title = 'Sending DOI %s to Crossref (batch %s)' % (
            deposit.doi, deposit.doi_batch_id)
        log_event(session, {'title': log_title, 'type': 'submission', 'status': 'info', 'deposit_code': code})

        try:
            result = crossref_client.register_doi(code, deposit.submission_xml)
        except Exception as exc:
            log_title = (
                'Could not send DOI %s to Crossref API; retrying at %s '
                '(batch %s)' % (
                    deposit.doi,
                    datetime.now() + REGISTER_DOI_DELAY_RETRY_TD,
                    deposit.doi_batch_id))
            logger.error(log_title)

            now = datetime.now()
            deposit.submission_status = 'waiting'
            deposit.submission_updated_at = now
            deposit.updated_at = now

            log_event(session, {'title': log_title, 'body': str(exc), 'type': 'submission', 'status': 'error', 'deposit_code': code})
            exc_class, exc_log_title = (ComunicationError, log_title)
        else:

            if result.status_code != 200:
                log_title = (
                    'Crossref API returned HTTP %d for DOI %s; retrying at %s '
                    '(batch %s)' % (
                        result.status_code,
                        deposit.doi,
                        datetime.now() + REGISTER_DOI_DELAY_RETRY_TD,
                        deposit.doi_batch_id))
                logger.error(log_title)
                now = datetime.now()
                deposit.submission_log = log_title
                deposit.submission_status = 'error'
                deposit.submission_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'body': 'HTTP status code %d' % result.status_code, 'type': 'submission', 'status': 'error', 'deposit_code': code})
                exc_class, exc_log_title = (RequestError, log_title)

            elif result.status_code == 200 and 'SUCCESS' in result.text:
                log_title = 'DOI %s sent successfully to Crossref (batch %s)' % (
                    deposit.doi, deposit.doi_batch_id)
                logger.debug(log_title)
                now = datetime.now()
                deposit.submission_status = 'success'
                deposit.submission_updated_at = now
                deposit.updated_at = now

                log_event(session, {'title': log_title, 'body': result.text, 'type': 'submission', 'status': 'success', 'deposit_code': code})
                return code

            else:
                log_title = 'Crossref rejected DOI %s (batch %s)' % (
                    deposit.doi, deposit.doi_batch_id)
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

                log_event(session, {'title': log_title, 'body': doi_batch_status or '', 'type': 'feedback', 'status': 'info', 'deposit_code': code})
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
    return enqueue_document(code, collection, skip_deposited=False)


@app.task(bind=True, throws=(ChainAborted,), task_time_limit=60, 
        autoretry_for=(ServerError,), retry_backoff=True)
@log_call
def registry_dispatcher_document_skip_deposited(self, code, collection):
    """
    This task receive a list of codes that should be queued for DOI registry
    """
    return enqueue_document(code, collection, skip_deposited=True)

