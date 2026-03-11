import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from doi_request.models import Base
from doi_request.models.depositor import Deposit
from doi_request.views import search_deposits


class DepositSearchTest(unittest.TestCase):

    def setUp(self):
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine)
        self.session = sessionmaker(bind=engine)()
        started_at = datetime(2026, 3, 11, tzinfo=timezone.utc)

        self.session.add_all([
            Deposit(
                code='scl_S1518-29242026000101002',
                pid='S1518-29242026000101002',
                issn='1518-2924',
                volume='1',
                number='1',
                issue_label='v1n1',
                journal='Revista de Testes',
                journal_acronym='rtest',
                collection_acronym='scl',
                publication_year=2026,
                xml_file_name='S1518-29242026000101002.xml',
                prefix='10.1590',
                doi='10.1590/S1518-29242026000101002',
                started_at=started_at,
                updated_at=started_at,
            ),
            Deposit(
                code='scl_S0102-311X2026000100001',
                pid='S0102-311X2026000100001',
                issn='0102-311X',
                volume='2',
                number='3',
                issue_label='v2n3',
                journal='Cadernos de Saude Publica',
                journal_acronym='csp',
                collection_acronym='scl',
                publication_year=2026,
                xml_file_name='S0102-311X2026000100001.xml',
                prefix='10.1590',
                doi='10.1590/S0102-311X2026000100001',
                started_at=started_at,
                updated_at=started_at,
            ),
        ])
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_search_deposits_matches_partial_pid(self):
        query, search_term = search_deposits(
            self.session.query(Deposit),
            '292420260001',
        )

        self.assertEqual(search_term, '292420260001')
        self.assertEqual(
            [item.pid for item in query.all()],
            ['S1518-29242026000101002'],
        )

    def test_search_deposits_matches_other_text_fields(self):
        query, _ = search_deposits(
            self.session.query(Deposit),
            'saude',
        )

        self.assertEqual(
            [item.journal_acronym for item in query.all()],
            ['csp'],
        )

    def test_search_deposits_ignores_blank_input(self):
        query, search_term = search_deposits(
            self.session.query(Deposit),
            '   ',
        )

        self.assertEqual(search_term, '')
        self.assertEqual(query.count(), 2)
