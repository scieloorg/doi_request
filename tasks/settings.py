import os
from datetime import timedelta

from crossref.client import CrossrefClient
from utils.settings import asbool


REQUEST_DOI_MAX_RETRY = int(os.environ.get('REQUEST_DOI_MAX_RETRY', '20000'))
REGISTER_DOI_MAX_RETRY = int(os.environ.get('REGISTER_DOI_MAX_RETRY', '20000'))
REQUEST_DOI_DELAY_RETRY = int(os.environ.get('REQUEST_DOI_DELAY_RETRY', '600'))
REGISTER_DOI_DELAY_RETRY = int(os.environ.get('REGISTER_DOI_DELAY_RETRY', '600'))
RELATIONS_MAX_RETRY = REQUEST_DOI_MAX_RETRY
RELATIONS_DELAY_RETRY = REQUEST_DOI_DELAY_RETRY
REQUEST_DOI_DELAY_RETRY_TD = timedelta(seconds=REQUEST_DOI_DELAY_RETRY)
REGISTER_DOI_DELAY_RETRY_TD = timedelta(seconds=REGISTER_DOI_DELAY_RETRY)
SUGGEST_DOI_IDENTIFICATION = asbool(os.environ.get('SUGGEST_DOI_IDENTIFICATION', False))
CROSSREF_SCHEMA_VERSION = os.environ.get('CROSSREF_SCHEMA_VERSION', '5.5.0')
CROSSREF_SCHEMA_NAMESPACE = (
    'http://www.crossref.org/schema/%s' % CROSSREF_SCHEMA_VERSION
)
CROSSREF_XSD_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'xsd',
    'crossref%s.xsd' % CROSSREF_SCHEMA_VERSION
))
CROSSREF_PREFIX = os.environ.get('CROSSREF_PREFIX', None)
CROSSREF_API_USER = os.environ.get('CROSSREF_API_USER', None)
CROSSREF_API_PASSWORD = os.environ.get('CROSSREF_API_PASSWORD', None)
CROSSREF_DEPOSITOR_NAME = os.environ.get('CROSSREF_DEPOSITOR_NAME', None)
CROSSREF_DEPOSITOR_EMAIL = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None)
CROSSREF_DEPOSIT_URL = os.environ.get('CROSSREF_DEPOSIT_URL', 'https://doi.crossref.org')
CROSSREF_API_URL = os.environ.get('CROSSREF_API_URL', 'https://api.crossref.org')
ARTICLEMETA_THRIFTSERVER = os.environ.get(
    'ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621')

crossref_client = CrossrefClient(
    CROSSREF_PREFIX, CROSSREF_API_USER, CROSSREF_API_PASSWORD,
    deposit_url=CROSSREF_DEPOSIT_URL, api_url=CROSSREF_API_URL)
