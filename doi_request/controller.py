from tasks.celery import registry_dispatcher


class Depositor(object):

    def deposit_by_pids(self, pids_list):
        """
        Receive a list of pids and collection to registry their dois.
        scl
        """
        registry_dispatcher.delay(pids_list)
