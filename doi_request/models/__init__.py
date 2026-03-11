import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

DBSession = scoped_session(sessionmaker())
Base = declarative_base()
PlainSession = sessionmaker(expire_on_commit=False)
_PLAIN_SESSION_CONFIGURED = False


def normalize_sql_engine_url(url):
    if url.startswith('postgresql://'):
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql+psycopg://', 1)
    return url


def create_engine_from_env():
    url = os.environ.get('SQL_ENGINE', 'sqlite:///:memory:')
    return create_engine(
        normalize_sql_engine_url(url),
        pool_pre_ping=True,
    )


def create_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


def configure_session_engine(engine=None):
    global _PLAIN_SESSION_CONFIGURED

    engine = engine or create_engine_from_env()
    DBSession.configure(bind=engine)
    PlainSession.configure(bind=engine)
    _PLAIN_SESSION_CONFIGURED = True
    return engine


def initialize_sql(engine):
    configure_session_engine(engine)
    Base.metadata.create_all(engine)

@contextmanager
def transactional_session():
    if not _PLAIN_SESSION_CONFIGURED:
        configure_session_engine()

    session = PlainSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
