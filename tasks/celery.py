from datetime import datetime
import time
from urllib.parse import quote_plus

import requests
from celery import Celery

from doi_request.models import transactional_session
from doi_request.models.reprocess import ReprocessJob, ReprocessLog


app = Celery('tasks', broker='redis://redis:6379/0')


@app.task(bind=True, name='tasks.celery.reprocess_dois')
def reprocess_dois(self, job_id, entries, user, rate_limit_seconds=1.0, dry_run=False):
    """Validate DOIs against Crossref and store audit logs."""
    try:
        with transactional_session() as session:
            job = session.query(ReprocessJob).get(job_id)
            if job is None:
                return None
            job.status = 'running'
            job.started_at = datetime.utcnow()
            session.add(job)
            session.commit()

        processed = 0
        skipped = 0

        for value in entries:
            if '/' not in value:
                with transactional_session() as session:
                    session.add(ReprocessLog(
                        job_id=job_id,
                        doi=value,
                        valid=True,
                        reason='prefix provided; included for later filtering'
                    ))
                processed += 1
                time.sleep(rate_limit_seconds)
                continue

            url = 'https://api.crossref.org/works/{}'.format(quote_plus(value))
            reason = 'not found in Crossref (404)'
            valid = False

            for attempt in range(3):
                try:
                    response = requests.get(url, timeout=15)
                except Exception as exc:
                    reason = 'request error: %s' % exc
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        continue
                    break

                if response.status_code == 200:
                    valid = True
                    reason = 'exists in Crossref'
                    break
                if response.status_code == 404:
                    reason = 'not found in Crossref (404)'
                    break
                reason = 'Crossref HTTP error %s' % response.status_code
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue

            with transactional_session() as session:
                session.add(ReprocessLog(job_id=job_id, doi=value, valid=valid, reason=reason))

            if valid:
                processed += 1
            else:
                skipped += 1

            time.sleep(rate_limit_seconds)

        with transactional_session() as session:
            job = session.query(ReprocessJob).get(job_id)
            if job:
                job.processed = processed
                job.skipped = skipped
                job.finished_at = datetime.utcnow()
                job.status = 'finished'
                job.message = 'validated %s DOI(s); skipped %s DOI(s)' % (processed, skipped)
                session.add(job)

        return {'processed': processed, 'skipped': skipped}

    except Exception as exc:
        with transactional_session() as session:
            job = session.query(ReprocessJob).get(job_id)
            if job:
                job.status = 'failed'
                job.finished_at = datetime.utcnow()
                job.message = str(exc)
                session.add(job)
        raise
