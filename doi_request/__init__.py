import os
from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from doi_request.models import initialize_sql


VERSION = '1.0.0'


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


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)

    # Database Config
    engine = create_engine(os.environ.get('SQL_ENGINE', 'sqlite:///:memory:'))
    static_assets = os.environ.get('STATIC_MEDIA', 'media')
    config.registry.dbmaker = sessionmaker(bind=engine)
    config.scan('doi_request.models')  # the "important" line
    initialize_sql(engine)
    config.add_request_method(db, reify=True)
    config.add_request_method(version)

    config.include('pyramid_mako')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_static_view('media', 'media', cache_max_age=3600)
    config.add_route('list_deposits', '/')
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
    navegation_session_factory = SignedCookieSessionFactory('sses_navegation')
    config.set_session_factory(navegation_session_factory)

    config.scan()
    return config.make_wsgi_app()
