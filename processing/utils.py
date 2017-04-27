import re
import logging
import re

try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

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
