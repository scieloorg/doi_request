import base64
import hashlib
import hmac
import json
import os
from functools import wraps

from pyramid.httpexceptions import HTTPFound, HTTPForbidden

from doi_request.models.depositor import AuditLog, User

PASSWORD_ITERATIONS = 600000
PASSWORD_SALT_BYTES = 16


def _b64encode(value):
    return base64.b64encode(value).decode('ascii')


def _b64decode(value):
    return base64.b64decode(value.encode('ascii'))


def hash_password(password):
    if not password:
        raise ValueError('password must not be empty')

    salt = os.urandom(PASSWORD_SALT_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        PASSWORD_ITERATIONS,
    )
    return 'pbkdf2_sha256${iterations}${salt}${digest}'.format(
        iterations=PASSWORD_ITERATIONS,
        salt=_b64encode(salt),
        digest=_b64encode(derived_key),
    )


def verify_password(password, stored_password_hash):
    if not password or not stored_password_hash:
        return False

    try:
        algorithm, iterations, salt, stored_digest = stored_password_hash.split('$', 3)
    except ValueError:
        return False

    if algorithm != 'pbkdf2_sha256':
        return False

    derived_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        _b64decode(salt),
        int(iterations),
    )
    return hmac.compare_digest(_b64encode(derived_key), stored_digest)


def get_authenticated_user(request):
    user_id = request.session.get('auth_user_id')
    if not user_id:
        return None
    return request.db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()


def login_user(request, user):
    request.session['auth_user_id'] = user.id


def logout_user(request):
    request.session.pop('auth_user_id', None)


def require_login(view_callable):
    @wraps(view_callable)
    def wrapped(request, *args, **kwargs):
        if request.current_user is None:
            login_url = request.route_url('login', _query={'next': request.path_qs or request.path})
            return HTTPFound(location=login_url)
        return view_callable(request, *args, **kwargs)

    return wrapped


def require_admin(view_callable):
    @wraps(view_callable)
    def wrapped(request, *args, **kwargs):
        if request.current_user is None:
            login_url = request.route_url('login', _query={'next': request.path_qs or request.path})
            return HTTPFound(location=login_url)
        if not request.current_user.is_admin:
            raise HTTPForbidden()
        return view_callable(request, *args, **kwargs)

    return wrapped


def record_audit_action(
    request,
    action,
    target_type='',
    target_id='',
    target_label='',
    details=None,
    actor_user=None,
):
    actor_user = actor_user or request.current_user
    payload = '' if details is None else json.dumps(details, ensure_ascii=True, sort_keys=True)
    audit_log = AuditLog(
        actor_user=actor_user,
        actor_username=actor_user.username if actor_user else '',
        action=action,
        target_type=target_type or '',
        target_id=str(target_id or ''),
        target_label=target_label or '',
        details=payload,
    )
    request.db.add(audit_log)
    return audit_log
