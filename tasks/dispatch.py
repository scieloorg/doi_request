"""Cria o depósito e enfileira a cadeia de registro."""
import logging
from datetime import datetime

from articlemeta.client import ThriftClient

from doi_request.models.depositor import Deposit
from doi_request.models import transactional_session
from tasks.settings import (
    ARTICLEMETA_THRIFTSERVER,
    CROSSREF_PREFIX,
    SUGGEST_DOI_IDENTIFICATION,
)


logger = logging.getLogger(__name__)


def registry_dispatcher_document(code, collection, skip_deposited):
    """Lê o documento no ArticleMeta, grava o depósito e inicia a cadeia."""
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

    from tasks.celery import (
        chain,
        load_xml_from_articlemeta,
        resolve_relations,
        submission_chain,
        triage_deposit,
    )
    chain(
        triage_deposit.s(code).set(queue='dispatcher'),
        load_xml_from_articlemeta.s().set(queue='dispatcher'),
        resolve_relations.s().set(queue='dispatcher'),
        *submission_chain()
    ).delay()
