import re
import logging
try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

try:
    from raven.handlers.logging import SentryHandler
    from raven.conf import setup_logging
except ImportError:
    SentryHandler = setup_logging = None


logger = logging.getLogger(__name__)

REGEX_ISSN = re.compile(r"^[0-9]{4}-[0-9]{3}[0-9xX]$")

settings = {}


def ckeck_given_issns(issns):
    valid_issns = []

    for issn in issns:
        if not REGEX_ISSN.match(issn):
            continue
        valid_issns.append(issn)

    return valid_issns


def setup_sentry(dsn):
    if SentryHandler and setup_logging:
        if dsn:
            handler = SentryHandler(dsn)
            handler.setLevel(logging.ERROR)
            setup_logging(handler)
            logger.info('log handler for Sentry was successfuly set up')
        else:
            logger.info('cannot setup handler for Sentry: missing DSN')
    else:
        logger.info('cannot setup handler for Sentry: make sure raven is installed')
