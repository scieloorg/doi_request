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
from doi_request.control_manager import check_session
from doi_request.control_manager import base_data_manager

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

    total = deposits.count()
    deposits = deposits.order_by(desc('started_at')).limit(LIMIT).offset(request.session['offset'])
    data['deposits'] = deposits
    data['status_to_template'] = template_choices.STATUS_TO_TEMPLATE
    data['filter_from_date'] = from_date
    data['filter_to_date'] = to_date
    data['filter_feedback_status'] = request.session['filter_feedback_status']
    data['filter_submission_status'] = request.session['filter_submission_status']
    data['filter_issn'] = request.session['filter_issn']
    data['filter_prefix'] = request.session['filter_prefix']
    data['offset'] = request.session['offset']
    data['limit'] = LIMIT if LIMIT <= total else total + 1
    data['total'] = total
    data['page'] = int((request.session['offset']/LIMIT)+1)
    data['total_pages'] = int((total/LIMIT)+1)

    return data

@view_config(route_name='deposit', renderer='templates/deposit.mako')
@check_session
@base_data_manager
def deposit(request):

    data = request.data_manager

    code = request.matchdict['deposit_item_code']

    try:
        deposit = request.db.query(Deposit).filter(Deposit.code == code).first()
    except IndexError:
        raise exc.HTTPNotFound()

    data['deposit'] = deposit
    data['timeline'] = deposit.timeline
    data['status_to_template'] = template_choices.STATUS_TO_TEMPLATE

    return data

@view_config(route_name='post_deposit')
def post_deposit(request):

    code = request.matchdict['deposit_item_code']
    collection, pid = code.split('_')

    depositor.deposit_by_pid(pid, collection)

    return HTTPFound('/deposit/%s' % code)

@view_config(route_name='help', renderer='templates/help.mako')
@check_session
@base_data_manager
def help(request):

    data = request.data_manager

    return data
