from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory

from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker

from setup import VERSION


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
    engine = engine_from_config(settings, prefix='sqlalchemy.')
    config.registry.dbmaker = sessionmaker(bind=engine)
    config.scan('doi_request.models')  # the "important" line
    initialize_sql(engine)

    config.add_request_method(db, reify=True)
    config.include('pyramid_mako')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('list_deposits', '/')
    config.add_route('help', '/help')
    config.add_route('deposit', '/deposit/{deposit_item_code}')
    config.add_route('post_deposit', '/deposit/post/{deposit_item_code}')

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
