from pyramid.config import Configurator
from pyramid.session import SignedCookieSessionFactory


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('pyramid_mako')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('list_deposits', '/')
    config.add_route('help', '/help')
    config.add_route('deposit', '/deposit/{deposit_item_code}')

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
