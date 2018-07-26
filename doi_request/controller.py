import logging

from tasks.celery import registry_dispatcher_document


logger = logging.getLogger(__name__)


class Depositor(object):

    def deposit_by_pids(self, pids_list):
        """
        Receive a list of pids and collection to registry their dois.
        scl
        """
        for item in pids_list:
            collection, code = item.split('_')
            registry_dispatcher_document.delay(code, collection)
            logger.info('enqueued deposit for "%s"', item)

