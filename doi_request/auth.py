import base64
import hashlib
import hmac
import os
from functools import wraps

from pyramid.httpexceptions import HTTPFound

from doi_request.models.depositor import User

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
