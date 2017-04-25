import os

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

DBSession = scoped_session(sessionmaker())
Base = declarative_base()


def create_engine_from_env():
    return create_engine(os.environ.get('SQL_ENGINE', 'sqlite:///:memory:'))


def configure_session_engine(engine=None):
    DBSession.configure(bind=engine or create_engine_from_env())


def initialize_sql(engine):
    configure_session_engine(engine)
    Base.metadata.bind = engine
    Base.metadata.create_all(engine)
