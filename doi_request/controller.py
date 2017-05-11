import pickle

from tasks.celery import (
    registry_dispatcher_document,
    registry_dispatcher
)


class Depositor(object):

    def deposit(self, document):
        """
        Receive a Xylose document ArticleMeta
        """
        pfile = io.BytesIO()
        doc = pickle.dumps(document)
        registry_dispatcher_document.delay(doc)

    def deposit_by_pids(self, pids_list):
        """
        Receive a list of pids and collection to registry their dois.
        scl
        """
        registry_dispatcher.delay(pids_list)
