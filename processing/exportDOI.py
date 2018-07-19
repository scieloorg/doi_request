# coding: utf-8
"""
Este processamento realiza a exportação de registros SciELO para o Crossref
"""
import os
import argparse
import logging
from datetime import datetime, timedelta

from articlemeta.client import ThriftClient

from doi_request.controller import Depositor
from processing import utils

logger = logging.getLogger('exportDOI')

LOGGER_FMT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

FROM = datetime.now() - timedelta(days=30)
FROM = FROM.isoformat()[:10]
UNTIL = datetime.now().isoformat()[:10]


class ExportDOI(object):

    def __init__(self, collection, issns=None, from_date=FROM,
            until_date=UNTIL):

        self._articlemeta = ThriftClient(domain=os.environ.get(
            'ARTICLEMETA_THRIFTSERVER', 'articlemeta.scielo.org:11621'))
        self._depositor = Depositor()
        self.collection = collection
        self.from_date = from_date
        self.until_date = until_date
        self.issns = issns or [None]

    def run(self):
        logger.info('started collecting articles with processing dates '
                    'between "%s" and "%s"', self.from_date, self.until_date)
        count = 0
        for issn in self.issns:

            for document in self._articlemeta.documents(
                    collection=self.collection, issn=issn,
                    from_date=self.from_date, until_date=self.until_date,
                    only_identifiers=True):

                code = '_'.join([document.collection, document.code])
                logger.info('collecting document for deposit: %s', code)
                self._depositor.deposit_by_pids([code])
                count += 1

        logger.info('finished collecting documents. total: %d', count)


def main():

    parser = argparse.ArgumentParser(
        description='Load documents into DOAJ'
    )

    parser.add_argument(
        'issns',
        nargs='*',
        help='ISSN\'s separated by spaces'
    )

    parser.add_argument(
        '--issns_file',
        '-i',
        default=None,
        help='Full path to a txt file within a list of ISSNs to be exported'
    )

    parser.add_argument(
        '--collection',
        '-c',
        help='Collection Acronym',
        required=True
    )

    parser.add_argument(
        '--from_date',
        '-f',
        default=FROM,
        help='ISO date like %s' % FROM
    )

    parser.add_argument(
        '--until_date',
        '-g',
        default=UNTIL,
        help='ISO date like %s' % UNTIL
    )

    parser.add_argument(
        '--date_range',
        '-r',
        type=int,
        help='Days from the current date to setup the processing date range. It will overwrite any definition of the arguments from_date and until_date'
    )

    parser.add_argument(
        '--logging_level',
        '-l',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Logging level'
    )

    parser.add_argument(
        '--sentry_handler',
        default='',
        help='Sentry DSN. This option has precedence over SENTRY_HANDLER env var'
    )
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.logging_level.upper(), 'INFO'),
            format=LOGGER_FMT)
    utils.setup_sentry(args.sentry_handler or os.environ.get('SENTRY_HANDLER', ''))

    logger.info('Dumping data for: %s' % args.collection)

    issns = None
    if len(args.issns) > 0:
        issns = utils.ckeck_given_issns(args.issns)

    issns_from_file = None
    if args.issns_file:
        with open(args.issns_file, 'r') as f:
            issns_from_file = utils.ckeck_given_issns([i.strip() for i in f])

    if issns:
        issns += issns_from_file if issns_from_file else []
    else:
        issns = issns_from_file if issns_from_file else []

    if args.date_range:
        from_date = datetime.now() - timedelta(days=args.date_range)
        args.from_date = from_date.isoformat()[:10]
        args.until_date = datetime.now().isoformat()[:10]

    export = ExportDOI(
        args.collection,
        issns,
        from_date=args.from_date,
        until_date=args.until_date,
    )

    export.run()
