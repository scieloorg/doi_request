import os
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"pkg_resources is deprecated as an API\..*",
    category=UserWarning,
    module=r"pyramid\.path",
)

VERSION = '1.5.0'


def version(request):
    return VERSION


def db(request):
    maker = request.registry.dbmaker
    session = maker()

    def cleanup(request):
        if request.exception is not None:
            session.rollback()
        else:
            session.commit()
        session.close()
    request.add_finished_callback(cleanup)

    return session


def current_user(request):
    from doi_request.auth import get_authenticated_user

    return get_authenticated_user(request)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    from pyramid.config import Configurator
    from pyramid.session import SignedCookieSessionFactory

    from doi_request.models import (
        create_engine_from_env,
        create_session_factory,
        initialize_sql,
    )

    config = Configurator(settings=settings)

    # Database Config
    engine = create_engine_from_env()
    static_assets = os.environ.get('STATIC_MEDIA', 'media')
    config.registry.engine = engine
    config.registry.dbmaker = create_session_factory(engine)
    config.scan('doi_request.models')  # the "important" line
    initialize_sql(engine)
    config.add_request_method(db, reify=True)
    config.add_request_method(version)
    config.add_request_method(current_user, reify=True)

    config.include('pyramid_mako')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('media', static_assets, cache_max_age=3600)
    config.add_route('list_deposits', '/')
    config.add_route('login', '/login')
    config.add_route('logout', '/logout')
    config.add_route('help', '/help')
    config.add_route('deposit_request', '/deposit/request')
    config.add_route('expenses', '/expenses')
    config.add_route('expenses_details', '/expenses/details')
    config.add_route('deposit_post', '/deposit/post')
    config.add_route('deposit', '/deposit')
    config.add_route('downloads', '/downloads')

    config.add_subscriber('doi_request.subscribers.add_renderer_globals',
                          'pyramid.events.BeforeRender')
    config.add_subscriber('doi_request.subscribers.add_localizer',
                          'pyramid.events.NewRequest')
    config.add_translation_dirs('doi_request:locale')

    # Session config
    navigation_session_secret = os.environ.get('SESSION_SECRET', 'sses_navegation')
    navegation_session_factory = SignedCookieSessionFactory(navigation_session_secret)
    config.set_session_factory(navegation_session_factory)

    config.scan()
    return config.make_wsgi_app()
