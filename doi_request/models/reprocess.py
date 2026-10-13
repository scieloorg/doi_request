from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship

from doi_request.models import Base


class ReprocessJob(Base):
    __tablename__ = 'reprocess_job'

    id = Column(Integer, primary_key=True)
    created_by = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), default='pending')
    total = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    dry_run = Column(Boolean, default=True)
    prefixes_or_dois = Column(Text, nullable=True)
    message = Column(Text, nullable=True)

    logs = relationship('ReprocessLog', backref='job', cascade='all, delete-orphan')


class ReprocessLog(Base):
    __tablename__ = 'reprocess_log'

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey('reprocess_job.id'), nullable=False)
    doi = Column(String(300), nullable=False)
    valid = Column(Boolean, default=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
