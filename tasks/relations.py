from datetime import datetime
import logging

from sqlalchemy import func

from crossref import relations
from doi_request.models.depositor import Deposit
from tasks.exceptions import RelatedDocumentNotFound, RelationCycleError
from tasks.logging import describe_relation, log_relation_event
from tasks.settings import crossref_client
from tasks.xml import parse_xml, serialize_xml


logger = logging.getLogger(__name__)


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
        principal = session.query(Deposit).filter(
            func.upper(Deposit.doi) == target_doi.upper()
        ).first()

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
    now = datetime.now()
    deposit.submission_status = 'waiting'
    deposit.submission_updated_at = now
    deposit.submission_xml = serialize_xml(xml_doc)
    deposit.updated_at = now
