import os
import logging
import logging.config
from datetime import datetime
from io import BytesIO, StringIO

from lxml import etree

from articlemeta.client import ThriftClient
from tasks.celery import register_doi, request_doi_status
from doi_request.models.depositor import Deposit, LogEvent
from doi_request.models import DBSession

logger = logging.getLogger(__name__)

CROSSREF_XSD = open(os.path.dirname(__file__)+'/../xsd/crossref4.4.0.xsd')
CROSSREF_PREFIX = os.environ.get('CROSSREF_PREFIX', None)
CROSSREF_API_USER = os.environ.get('CROSSREF_API_USER', None)
CROSSREF_API_PASSWORD = os.environ.get('CROSSREF_API_PASSWORD', None)
CROSSREF_DEPOSITOR_NAME = os.environ.get('CROSSREF_DEPOSITOR_NAME', None)
CROSSREF_DEPOSITOR_EMAIL = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None)


class Depositor(object):

    def __init__(self, test_mode=False):

        self._articlemeta = ThriftClient(domain=os.environ.get('ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621'))
        self._parse_schema()

    def deposit(self, document):
        register_dispatcher.apply_async(document)

    def deposit_by_pid(self, pid, collection):

        document = self._articlemeta.document(pid, collection)

        self.deposit(document)
