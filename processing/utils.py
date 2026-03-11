import re
import logging

from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.logging import LoggingIntegration


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
    if dsn:
        sentry_init(
            dsn=dsn,
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                )
            ],
        )
        logger.info('log handler for Sentry was successfully set up')
    else:
        logger.info('cannot setup handler for Sentry: missing DSN')
