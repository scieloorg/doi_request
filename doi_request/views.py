from datetime import datetime
from datetime import timedelta

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
import pyramid.httpexceptions as exc
from mongoengine.queryset.visitor import Q

from sqlalchemy import desc, func, or_

from doi_request.models.depositor import Deposit, Expenses
from doi_request.models import DBSession
from doi_request import template_choices
from doi_request import controller
from doi_request.control_manager import check_session
from doi_request.control_manager import base_data_manager
from doi_request.utils import pagination_ruler

depositor = controller.Depositor()
LIMIT = 100

@view_config(route_name='list_deposits', renderer='templates/deposits.mako')
@check_session
@base_data_manager
def list_deposits(request):
    data = request.data_manager
    filter_pid_doi = request.GET.get('filter_pid_doi', None)
    to_date = request.session['filter_start_range'].split('-')[1].strip()
    to_date_dt = datetime.strptime(request.session['filter_start_range'].split('-')[1].strip(), '%m/%d/%Y')
    from_date = request.session['filter_start_range'].split('-')[0].strip()
    from_date_dt = datetime.strptime(request.session['filter_start_range'].split('-')[0].strip(), '%m/%d/%Y')
    total = 0
    if filter_pid_doi:
        deposits = request.db.query(Deposit).filter(or_(Deposit.doi == filter_pid_doi, Deposit.pid == filter_pid_doi))
    else:
        deposits = request.db.query(Deposit).filter(or_(Deposit.started_at >= from_date_dt, Deposit.started_at <= to_date_dt))
        if request.session['filter_feedback_status']:
            deposits = deposits.filter(Deposit.feedback_status == request.session['filter_feedback_status'])
        if request.session['filter_submission_status']:
            deposits = deposits.filter(Deposit.submission_status == request.session['filter_submission_status'])
        if request.session['filter_issn']:
            deposits = deposits.filter(Deposit.issn == request.session['filter_issn'])
        if request.session['filter_prefix']:
            deposits = deposits.filter(Deposit.prefix == request.session['filter_prefix'])
        if request.session['filter_journal_acronym']:
            deposits = deposits.filter(Deposit.journal_acronym == request.session['filter_journal_acronym'])
        if request.session['filter_has_valid_references']:
            deposits = deposits.filter(Deposit.has_submission_xml_valid_references == request.session['filter_has_valid_references'])

    total = deposits.count()
    request.session['offset'] = request.session['offset'] if request.session['offset'] < total else 0
    deposits = deposits.order_by(desc('started_at')).limit(LIMIT).offset(request.session['offset'] )
    data['deposits'] = deposits
    data['submission_status_to_template'] = template_choices.SUBMISSION_STATUS_TO_TEMPLATE
    data['feedback_status_to_template'] = template_choices.FEEDBACK_STATUS_TO_TEMPLATE
    data['filter_from_date'] = from_date
    data['filter_to_date'] = to_date
    data['filter_feedback_status'] = request.session['filter_feedback_status']
    data['filter_has_valid_references'] = request.session['filter_has_valid_references']
    data['filter_journal_acronym'] = request.session['filter_journal_acronym']
    data['filter_submission_status'] = request.session['filter_submission_status']
    data['filter_issn'] = request.session['filter_issn']
    data['filter_prefix'] = request.session['filter_prefix']
    data['offset'] = request.session['offset']
    data['limit'] = LIMIT if LIMIT <= total else total + 1
    data['total'] = total
    data['page'] = int((request.session['offset']/LIMIT)+1)
    data['pagination_ruler'] = pagination_ruler(LIMIT, total, request.session['offset'])
    data['total_pages'] = int((total/LIMIT)+1)
    data['navbar_active'] = 'deposits'

    return data

@view_config(route_name='deposit', renderer='templates/deposit.mako')
@check_session
@base_data_manager
def deposit(request):
    data = request.data_manager

    code = request.GET.get('code', '')

    deposit = request.db.query(Deposit).filter(Deposit.code == code).first()

    if not deposit:
        raise exc.HTTPNotFound()

    data['deposit'] = deposit
    data['timeline'] = deposit.timeline
    data['submission_status_to_template'] = template_choices.SUBMISSION_STATUS_TO_TEMPLATE
    data['feedback_status_to_template'] = template_choices.FEEDBACK_STATUS_TO_TEMPLATE
    data['timeline_status_to_template'] = template_choices.TIMELINE_STATUS_TO_TEMPLATE

    return data

@view_config(route_name='deposit_request', renderer='templates/deposit_request.mako')
@check_session
@base_data_manager
def deposit_request(request):

    data = request.data_manager

    data['navbar_active'] = 'deposit_request'

    return data

@view_config(route_name='expenses', renderer='templates/expenses.mako')
@check_session
@base_data_manager
def expenses(request):

    data = request.data_manager

    expenses = request.db.query(Expenses)

    expenses = request.db.query(
        func.date_trunc('month', Expenses.registry_date).label('registry_month'),
        func.sum(Expenses.cost
    ).label('total')).group_by('registry_month')

    data['navbar_active'] = 'expenses'
    data['expenses'] = expenses

    return data

@view_config(route_name='expenses_details', renderer='templates/expenses_details.mako')
@check_session
@base_data_manager
def expenses_details(request):

    data = request.data_manager

    period = request.GET.get('period', datetime.now().isoformat())
    period = datetime.strptime(period[0:10], '%Y-%m-%d')

    expenses = request.db.query(Expenses)

    total = expenses.count()
    request.session['expenses_offset'] = request.session['expenses_offset'] if request.session['expenses_offset'] < total else 0
    data['navbar_active'] = 'expenses'
    data['expenses'] = expenses
    data['offset'] = request.session['expenses_offset']
    data['limit'] = LIMIT if LIMIT <= total else total + 1
    data['total'] = total
    data['page'] = int((request.session['expenses_offset']/LIMIT)+1)
    data['pagination_ruler'] = pagination_ruler(LIMIT, total, request.session['expenses_offset'])
    data['total_pages'] = int((total/LIMIT)+1)
    data['period'] = period

    return data

@view_config(route_name='deposit_post')
@base_data_manager
def deposit_post(request):

    data = request.data_manager

    pids = request.GET.get('pids', '')

    for ndx, pid in enumerate(pids.split('\r')):
        if ndx > 9:
            break
        depositor.deposit_by_pid(pid.strip(), data['collection_acronym'])

    return HTTPFound('/')

@view_config(route_name='help', renderer='templates/help.mako')
@check_session
@base_data_manager
def help(request):

    data = request.data_manager

    return data
