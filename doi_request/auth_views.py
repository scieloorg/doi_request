from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from sqlalchemy import desc

from doi_request.auth import (
    login_user,
    logout_user,
    record_audit_action,
    require_admin,
    require_login,
    verify_password,
    hash_password,
)
from doi_request.control_manager import base_data_manager, check_session
from doi_request.models.depositor import AuditLog, User


def _dashboard_data(request):
    data = request.data_manager
    data['navbar_active'] = 'dashboard'
    if request.current_user.is_admin:
        data['users'] = request.db.query(User).order_by(User.username.asc()).all()
        data['audit_logs'] = request.db.query(AuditLog).order_by(desc(AuditLog.created_at)).limit(50).all()
    else:
        data['users'] = []
        data['audit_logs'] = request.db.query(AuditLog).filter(
            AuditLog.actor_user_id == request.current_user.id
        ).order_by(desc(AuditLog.created_at)).limit(30).all()
    return data


def _profile_data(request):
    data = request.data_manager
    data['navbar_active'] = 'profile'
    data['audit_logs'] = request.db.query(AuditLog).filter(
        AuditLog.actor_user_id == request.current_user.id
    ).order_by(desc(AuditLog.created_at)).limit(30).all()
    return data


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
        record_audit_action(
            request,
            'login',
            target_type='user',
            target_id=user.id,
            target_label=user.username,
            actor_user=user,
        )
        return HTTPFound(location=next_url or request.route_url('list_deposits'))

    record_audit_action(
        request,
        'login_failed',
        target_type='user',
        target_label=username,
        details={'username': username},
        actor_user=user,
    )
    return {
        'error_message': request.translate('Usuário ou senha inválidos'),
        'next_url': next_url,
        'username': username,
        'version': request.version(),
    }


@view_config(route_name='logout')
@require_login
def logout(request):
    user = request.current_user
    record_audit_action(
        request,
        'logout',
        target_type='user',
        target_id=user.id,
        target_label=user.username,
    )
    logout_user(request)
    return HTTPFound(location=request.route_url('login'))


@view_config(route_name='dashboard', renderer='templates/dashboard.mako', request_method='GET')
@require_login
@check_session
@base_data_manager
def dashboard(request):
    data = _dashboard_data(request)
    data['form_values'] = {'username': '', 'is_admin': False, 'is_active': True}
    data['error_message'] = ''
    return data


@view_config(route_name='dashboard', renderer='templates/dashboard.mako', request_method='POST')
@require_admin
@check_session
@base_data_manager
def dashboard_post(request):
    username = request.POST.get('username', '').strip()
    password = request.POST.get('password', '')
    is_admin = request.POST.get('is_admin') == 'on'
    is_active = request.POST.get('is_active') == 'on'

    data = _dashboard_data(request)
    data['form_values'] = {
        'username': username,
        'is_admin': is_admin,
        'is_active': is_active,
    }

    if not username or not password:
        data['error_message'] = request.translate('Usuário e senha são obrigatórios')
        return data

    existing_user = request.db.query(User).filter(User.username == username).first()
    if existing_user is not None:
        data['error_message'] = request.translate('Já existe um usuário com esse nome')
        return data

    user = User(
        username=username,
        password_hash=hash_password(password),
        is_active=is_active,
        is_admin=is_admin,
    )
    request.db.add(user)
    request.db.flush()
    record_audit_action(
        request,
        'user_created',
        target_type='user',
        target_id=user.id,
        target_label=user.username,
        details={'is_admin': user.is_admin, 'is_active': user.is_active},
    )
    request.session.flash(request.translate('Usuário criado com sucesso'), queue='success')
    return HTTPFound(location=request.route_url('dashboard'))


@view_config(route_name='profile', renderer='templates/profile.mako', request_method='GET')
@require_login
@check_session
@base_data_manager
def profile(request):
    data = _profile_data(request)
    data['error_message'] = ''
    return data


@view_config(route_name='profile', renderer='templates/profile.mako', request_method='POST')
@require_login
@check_session
@base_data_manager
def profile_post(request):
    data = _profile_data(request)
    current_password = request.POST.get('current_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    if not verify_password(current_password, request.current_user.password_hash):
        data['error_message'] = request.translate('Senha atual inválida')
        return data

    if not new_password:
        data['error_message'] = request.translate('A nova senha é obrigatória')
        return data

    if new_password != confirm_password:
        data['error_message'] = request.translate('A confirmação da senha não confere')
        return data

    request.current_user.password_hash = hash_password(new_password)
    record_audit_action(
        request,
        'password_changed',
        target_type='user',
        target_id=request.current_user.id,
        target_label=request.current_user.username,
    )
    request.session.flash(request.translate('Senha atualizada com sucesso'), queue='success')
    return HTTPFound(location=request.route_url('profile'))
