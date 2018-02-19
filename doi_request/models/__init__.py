import os
from contextlib import contextmanager

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

DBSession = scoped_session(sessionmaker())
Base = declarative_base()


def create_engine_from_env():
    return create_engine(os.environ.get('SQL_ENGINE', 'sqlite:///:memory:'))


def configure_session_engine(engine):
    DBSession.configure(bind=engine)


def initialize_sql(engine):
    configure_session_engine(engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)


PlainSession = sessionmaker(bind=create_engine_from_env())

@contextmanager
def transactional_session():
    session = PlainSession()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

