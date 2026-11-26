"""Registro de eventos das tarefas de depósito."""
import functools

from celery.utils.log import get_task_logger

from doi_request.models.depositor import LogEvent


logger = get_task_logger(__name__)


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


def log_relation_event(session, code, title, status, body=''):
    log_event(session, {
        'title': title,
        'body': body,
        'type': 'relation',
        'status': status,
        'deposit_code': code,
    })


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
