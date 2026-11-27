"""Custo de registro de um DOI no Crossref."""
from datetime import datetime

from doi_request.models.depositor import Expenses
from tasks.logging import log_event


def register_expenses(session, deposit):
    if session.query(Expenses).filter_by(doi=deposit.doi).first() is not None:
        log_event(session, {'title': 'Expenses already registered for DOI (%s)' % deposit.doi, 'type': 'feedback', 'status': 'info', 'deposit_code': deposit.code})
        return

    #crossref backfiles limit current year - 2.
    back_file_limit = int(datetime.now().strftime('%Y')) - 2
    expenses = Expenses()
    expenses.publication_year = deposit.publication_year
    expenses.registry_date = datetime.now()
    expenses.doi = deposit.doi
    expenses.cost = 0.15 if int(deposit.publication_year) < back_file_limit else 1
    expenses.retro = True if int(deposit.publication_year) < back_file_limit else False
    session.add(expenses)
