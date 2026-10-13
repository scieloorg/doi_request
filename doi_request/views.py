import os
from datetime import datetime
from urllib.parse import quote_plus
import json
import time

import requests
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from doi_request.models.reprocess import ReprocessJob


@view_config(route_name='reprocess', renderer='templates/reprocess.mako')
@check_session
@base_data_manager
def reprocess(request):
    data = request.data_manager
    data['navbar_active'] = 'reprocess'
    data['jobs'] = request.db.query(ReprocessJob).order_by('created_at desc').limit(25)
    return data


@view_config(route_name='reprocess_submit', renderer='templates/reprocess.mako', request_method='POST')
@check_session
@base_data_manager
def reprocess_submit(request):
    data = request.data_manager
    data['navbar_active'] = 'reprocess'

    user = request.session.get('_USER_', request.environ.get('REMOTE_USER', 'unknown'))
    raw_input = request.POST.get('dois_or_prefixes', '').strip()
    dry_run = request.POST.get('dry_run', 'on') in ('on', 'true', '1')
    rate_limit_seconds = float(request.POST.get('rate_limit_seconds', '1.0') or 1.0)

    entries = [line.strip() for line in raw_input.replace(',', '\n').splitlines() if line.strip()]
    if not entries:
        data['jobs'] = request.db.query(ReprocessJob).order_by('created_at desc').limit(25)
        data['preview_results'] = []
        data['error'] = 'Informe pelo menos um DOI ou prefixo.'
        return data

    job = ReprocessJob(
        created_by=user,
        prefixes_or_dois=raw_input,
        dry_run=dry_run,
        total=len(entries),
        status='pending'
    )
    request.db.add(job)
    request.db.flush()

    preview_results = []
    for value in entries:
        if '/' not in value:
            preview_results.append({
                'input': value,
                'type': 'prefix',
                'valid': True,
                'reason': 'prefix provided for filtering; no direct Crossref validation in preview'
            })
            continue

        url = 'https://api.crossref.org/works/{}'.format(quote_plus(value))
        try:
            response = requests.get(url, timeout=10)
        except Exception as exc:
            preview_results.append({
                'input': value,
                'type': 'doi',
                'valid': False,
                'reason': 'request error: %s' % exc
            })
            continue

        if response.status_code == 200:
            preview_results.append({
                'input': value,
                'type': 'doi',
                'valid': True,
                'reason': 'exists in Crossref'
            })
        elif response.status_code == 404:
            preview_results.append({
                'input': value,
                'type': 'doi',
                'valid': False,
                'reason': 'not found in Crossref (404)'
            })
        else:
            preview_results.append({
                'input': value,
                'type': 'doi',
                'valid': False,
                'reason': 'Crossref HTTP error %s' % response.status_code
            })

        time.sleep(rate_limit_seconds)

    job.message = json.dumps({'preview_count': len(preview_results)})
    job.status = 'previewed'
    request.db.add(job)
    request.db.flush()

    data['jobs'] = request.db.query(ReprocessJob).order_by('created_at desc').limit(25)
    data['preview_results'] = preview_results
    data['dry_run'] = dry_run
    return data
