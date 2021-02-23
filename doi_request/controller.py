import logging

from tasks.celery import (
    registry_dispatcher_document,
    registry_dispatcher_document_skip_deposited,
)


logger = logging.getLogger(__name__)


class Depositor(object):

    def deposit_by_pids(self, pids_list, skip_deposited=False):
        """
        Receive a list of pids and collection to registry their dois.
        scl
        """
        if skip_deposited:
            register_document = registry_dispatcher_document_skip_deposited
        else:
            register_document = registry_dispatcher_document

        for item in pids_list:
            collection, code = item.split('_')
            register_document.delay(code,
                                    collection)
            logger.info('enqueued deposit for "%s"', item)

