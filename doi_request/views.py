from pyramid.view import view_config
from doi_request.models import DepositItem
import pyramid.httpexceptions as exc
from mongoengine.queryset.visitor import Q

from doi_request import template_choices
from datetime import datetime
from datetime import timedelta

@view_config(route_name='list_deposits', renderer='templates/deposits.mako')
def list_deposits(request):
    to_date = datetime.now()
    from_date = to_date - timedelta(days=30)
    default_date_range = ' - '.join([
        from_date.strftime('%m/%d/%Y')[:10],
        to_date.strftime('%m/%d/%Y')[:10]]
    )
    locale = request.GET.get('_LOCALE_', request.locale_name)
    query = request.GET.get('query', None)
    feedback_status = request.GET.get('feedback_status', None)
    feedback_start_range = request.GET.get('feedback_start_range', default_date_range)

    to_date = feedback_start_range.split('-')[1].strip()
    to_date_dt = datetime.strptime(feedback_start_range.split('-')[1].strip(), '%m/%d/%Y')
    from_date = feedback_start_range.split('-')[0].strip()
    from_date_dt = datetime.strptime(feedback_start_range.split('-')[0].strip(), '%m/%d/%Y')

    if query:
        deposits = DepositItem.objects(Q(doi=query) | Q(pid=query))
    else:
        deposits = DepositItem.objects(Q(feedback_status=feedback_status) & Q(started_at__gte=from_date_dt) & Q(started_at__lte=to_date_dt))

    data = {}
    data['locale'] = locale
    data['deposits'] = deposits
    data['feedback_status_to_template'] = template_choices.FEEDBACK_STATUS_TO_TEMPLATE
    data['submission_status_to_template'] = template_choices.SUBMISSION_STATUS_TO_TEMPLATE
    data['filter_from_date'] = from_date
    data['filter_to_date'] = to_date

    return data

@view_config(route_name='deposit', renderer='templates/deposit.mako')
def deposit(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)
    code = request.matchdict['deposit_item_code']

    try:
        deposit = DepositItem.objects(pk=code)[0]
    except IndexError:
        raise exc.HTTPNotFound()

    data = {}
    data['locale'] = locale
    data['deposit'] = deposit
    data['timeline'] = deposit.timeline
    data['feedback_status_to_template'] = template_choices.FEEDBACK_STATUS_TO_TEMPLATE
    data['submission_status_to_template'] = template_choices.SUBMISSION_STATUS_TO_TEMPLATE

    deposit.timeline

    return data


@view_config(route_name='help', renderer='templates/help.mako')
def help(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)

    deposits = DepositItem.objects()

    data = {}
    data['locale'] = locale
    data['deposits'] = deposits

    return data
