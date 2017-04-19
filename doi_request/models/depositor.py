from doi_request.models import Base
from sqlalchemy import ForeignKey, Column, Unicode, Integer, String, Boolean, Text, DateTime
from sqlalchemy.orm import relationship


class Deposit(Base):
    __tablename__ = 'deposit'
    code = Column('code', String(27), unique=True, nullable=False, primary_key=True)
    pid = Column('pid', String(23), unique=True, nullable=False)
    collection_acronym = Column('collection_acronym', String(3), nullable=False)
    xml_file_name = Column('xml_file_name', String(32), nullable=False)
    prefix = Column('prefix', String(16), nullable=False)
    doi = Column('doi', String(128), nullable=False)
    doi_batch_id = Column('doi_batch_id', String(32))
    is_xml_valid = Column('is_xml_valid', Boolean, default=False)
    started_at = Column('started_at', DateTime(timezone=True), nullable=False)
    updated_at = Column('updated_at', DateTime(timezone=True), nullable=False)
    submission_xml = Column('submission_xml', Text, default='')
    submission_status = Column('submission_status', String(16), default='unknow')
    submission_updated_at = Column('submission_updated_at', DateTime(timezone=True))
    submission_response = Column('submission_response', Text, default='')
    feedback_xml = Column('feedback_xml', Text, default='')
    feedback_status = Column('feedback_status', String(16))
    feedback_updated_at = Column('feedback_updated_at', DateTime(timezone=True))
    log_events = relationship('LogEvent', back_populates='deposit', cascade="all, delete, delete-orphan")

    @property
    def timeline(self):
        return self.log_events


class LogEvent(Base):
    __tablename__ = 'logevent'
    id = Column(Integer, primary_key=True)
    date = Column('date', DateTime(timezone=True), nullable=False)
    title = Column('title', Text, nullable=False)
    body = Column('body', Text, default='')
    http_status_code = Column('http_status_code', Integer)
    type = Column('type', String(16), nullable=False)
    status = Column('status', String(16))
    deposit_code = Column('deposit_code', ForeignKey('deposit.code'))
    deposit = relationship("Deposit", back_populates="log_events")
