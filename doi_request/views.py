from pyramid.view import view_config
from doi_request.models import DepositItem
import pyramid.httpexceptions as exc

@view_config(route_name='dashboard', renderer='templates/dashboard.mako')
def dashboard(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)

    deposits = DepositItem.objects()

    data = {}
    data['locale'] = locale
    data['deposits'] = deposits

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

    return data


@view_config(route_name='help', renderer='templates/help.mako')
def help(request):

    locale = request.GET.get('_LOCALE_', request.locale_name)

    deposits = DepositItem.objects()

    data = {}
    data['locale'] = locale
    data['deposits'] = deposits

    return data
