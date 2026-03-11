from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from doi_request.auth import login_user, logout_user, verify_password
from doi_request.models.depositor import User


@view_config(route_name='login', renderer='templates/login.mako', request_method='GET')
def login_get(request):
    if request.current_user is not None:
        return HTTPFound(location=request.route_url('list_deposits'))

    return {
        'error_message': '',
        'next_url': request.GET.get('next', request.route_url('list_deposits')),
        'username': '',
        'version': request.version(),
    }


@view_config(route_name='login', renderer='templates/login.mako', request_method='POST')
def login_post(request):
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    next_url = request.POST.get('next', request.route_url('list_deposits'))

    user = request.db.query(User).filter(
        User.username == username,
        User.is_active.is_(True),
    ).first()

    if user and verify_password(password, user.password_hash):
        login_user(request, user)
        return HTTPFound(location=next_url or request.route_url('list_deposits'))

    return {
        'error_message': request.translate('Usuário ou senha inválidos'),
        'next_url': next_url,
        'username': username,
        'version': request.version(),
    }


@view_config(route_name='logout')
def logout(request):
    logout_user(request)
    return HTTPFound(location=request.route_url('login'))
