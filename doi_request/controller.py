from doi_request.models import DepositItem


class Deposits(object):

    def all_deposits(self):

        return DepositItem.objects()
