import os

from doi_request.depositor import Depositor

CROSSREF_PREFIX = os.environ.get('CROSSREF_PREFIX', None)
CROSSREF_API_USER = os.environ.get('CROSSREF_API_USER', None)
CROSSREF_API_PASSWORD = os.environ.get('CROSSREF_API_PASSWORD', None)
CROSSREF_DEPOSITOR_NAME = os.environ.get('CROSSREF_DEPOSITOR_NAME', None)
CROSSREF_DEPOSITOR_EMAIL = os.environ.get('CROSSREF_DEPOSITOR_EMAIL', None)


def depositor():
    return Depositor(
        CROSSREF_PREFIX, CROSSREF_API_USER, CROSSREF_API_PASSWORD, CROSSREF_DEPOSITOR_NAME, CROSSREF_DEPOSITOR_EMAIL
    )
