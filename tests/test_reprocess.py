import json
from unittest import mock

from doi_request.models import transactional_session
from doi_request.models.reprocess import ReprocessJob, ReprocessLog
from tasks.celery import reprocess_dois


def _fake_response(status_code, payload=b'{}'):
    class Response(object):
        def __init__(self, status_code, payload):
            self.status_code = status_code
            self.text = payload.decode('utf-8') if isinstance(payload, bytes) else payload
            self.content = payload
    return Response(status_code, payload)


@mock.patch('tasks.celery.requests.get')
def test_reprocess_validates_dois_and_logs(mock_get):
    def side_effect(url, timeout=15):
        if '10.1234/exists' in url:
            return _fake_response(200, b'{"status": "ok"}')
        if '10.1234/missing' in url:
            return _fake_response(404, b'{"status": "not-found"}')
        return _fake_response(500, b'{"status": "error"}')

    mock_get.side_effect = side_effect

    with transactional_session() as session:
        job = ReprocessJob(
            created_by='tester',
            prefixes_or_dois='10.1234/exists\n10.1234/missing',
            dry_run=False,
            total=2
        )
        session.add(job)
        session.flush()
        job_id = job.id

    result = reprocess_dois(job_id, ['10.1234/exists', '10.1234/missing'], 'tester', rate_limit_seconds=0.0, dry_run=False)

    assert result['processed'] == 1
    assert result['skipped'] == 1

    with transactional_session() as session:
        logs = session.query(ReprocessLog).filter(ReprocessLog.job_id == job_id).all()
        assert len(logs) == 2
        assert any(log.doi == '10.1234/exists' and log.valid for log in logs)
        assert any(log.doi == '10.1234/missing' and not log.valid for log in logs)
