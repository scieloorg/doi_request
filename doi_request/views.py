import os
from datetime import datetime
from datetime import timedelta

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
import pyramid.httpexceptions as exc
from mongoengine.queryset.visitor import Q

from sqlalchemy import or_
from sqlalchemy import desc

from doi_request.models.depositor import Deposit
from doi_request.models import DBSession
from doi_request import template_choices
from doi_request import controller

depositor = controller.Depositor()
LIMIT = 100


@view_config(route_name='list_deposits', renderer='templates/deposits.mako')
def list_deposits(request):
    to_date = datetime.now() + timedelta(days=1)
    from_date = to_date - timedelta(days=30)
    default_date_range = ' - '.join([
        from_date.strftime('%m/%d/%Y')[:10],
        to_date.strftime('%m/%d/%Y')[:10]]
    )
    locale = request.GET.get('_LOCALE_', request.locale_name)
    pid_doi = request.GET.get('pid_doi', None)
    submission_status = request.GET.get('submission_status', None)
    feedback_status = request.GET.get('feedback_status', None)
    issn = request.GET.get('issn', None)
    prefix = request.GET.get('prefix', None)
    feedback_start_range = request.GET.get('feedback_start_range', default_date_range)
    offset = int(request.GET.get('offset', 0))

    to_date = feedback_start_range.split('-')[1].strip()
    to_date_dt = datetime.strptime(feedback_start_range.split('-')[1].strip(), '%m/%d/%Y')
    from_date = feedback_start_range.split('-')[0].strip()
    from_date_dt = datetime.strptime(feedback_start_range.split('-')[0].strip(), '%m/%d/%Y')
    total = 0
    if pid_doi:
        deposits = DBSession.query(Deposit).filter(or_(Deposit.doi == pid_doi, Deposit.pid == pid_doi))
    else:
        deposits = DBSession.query(Deposit).filter(or_(Deposit.started_at >= from_date_dt, Deposit.started_at <= to_date_dt))
        if feedback_status:
            deposits = deposits.filter(Deposit.feedback_status == feedback_status)
        if submission_status:
            deposits = deposits.filter(Deposit.submission_status == submission_status)
        if issn:
            deposits = deposits.filter(Deposit.issn == issn)
        if prefix:
            deposits = deposits.filter(Deposit.prefix == prefix)

    total = deposits.count()
    deposits = deposits.order_by(desc('started_at')).limit(LIMIT).offset(offset)
    data = {}
    data['locale'] = locale
    data['deposits'] = deposits
    data['status_to_template'] = template_choices.STATUS_TO_TEMPLATE
    data['filter_from_date'] = from_date
    data['filter_to_date'] = to_date
    data['filter_feedback_status'] = feedback_status
    data['filter_submission_status'] = submission_status
    data['filter_issn'] = issn
    data['filter_prefix'] = prefix
    data['offset'] = offset
    data['limit'] = LIMIT
    data['total'] = total
    data['crossref_prefix'] = os.environ.get('CROSSREF_PREFIX', 'não definido')
    data['crossref_user_api'] = os.environ.get('CROSSREF_API_USER', 'não definido')
    data['crossref_depositor_name'] = os.environ.get('CROSSREF_DEPOSITOR_NAME', 'não definido')
    data['crossref_depositor_email'] = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', 'não definido')

    return data

@view_config(route_name='deposit', renderer='templates/deposit.mako')
def deposit(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)
    code = request.matchdict['deposit_item_code']

    try:
        deposit = DBSession.query(Deposit).filter(Deposit.code == code).first()
    except IndexError:
        raise exc.HTTPNotFound()

    data = {}
    data['locale'] = locale
    data['deposit'] = deposit
    data['timeline'] = deposit.timeline
    data['status_to_template'] = template_choices.STATUS_TO_TEMPLATE
    data['crossref_prefix'] = os.environ.get('CROSSREF_PREFIX', 'não definido')
    data['crossref_user_api'] = os.environ.get('CROSSREF_API_USER', 'não definido')
    data['crossref_depositor_name'] = os.environ.get('CROSSREF_DEPOSITOR_NAME', 'não definido')
    data['crossref_depositor_email'] = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', 'não definido')

    return data

@view_config(route_name='post_deposit')
def post_deposit(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)
    code = request.matchdict['deposit_item_code']
    collection, pid = code.split('_')

    depositor.deposit_by_pid(pid, collection)

    return HTTPFound('/deposit/%s' % code)

@view_config(route_name='help', renderer='templates/help.mako')
def help(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)

    data = {}
    data['locale'] = locale
    data['crossref_prefix'] = os.environ.get('CROSSREF_PREFIX', 'não definido')
    data['crossref_user_api'] = os.environ.get('CROSSREF_API_USER', 'não definido')
    data['crossref_depositor_name'] = os.environ.get('CROSSREF_DEPOSITOR_NAME', 'não definido')
    data['crossref_depositor_email'] = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', 'não definido')

    return data
