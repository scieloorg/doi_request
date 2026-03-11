import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from doi_request.models import Base
from doi_request.models.depositor import Deposit
from doi_request.views import apply_deposit_sort, search_deposits


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
                submission_status='waiting',
                feedback_status='success',
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
                submission_status='failure',
                feedback_status='error',
                started_at=started_at,
                updated_at=started_at,
            ),
            Deposit(
                code='scl_S0103-40142026000100002',
                pid='S0103-40142026000100002',
                issn='0103-4014',
                volume='4',
                number='2',
                issue_label='v4n2',
                journal='Estudos Avancados',
                journal_acronym='ea',
                collection_acronym='scl',
                publication_year=2026,
                xml_file_name='S0103-40142026000100002.xml',
                prefix='10.1590',
                doi='10.1590/S0103-40142026000100002',
                submission_status='notapplicable',
                feedback_status='waiting',
                started_at=started_at,
                updated_at=started_at,
            ),
            Deposit(
                code='scl_S0104-59702026000100003',
                pid='S0104-59702026000100003',
                issn='0104-5970',
                volume='5',
                number='1',
                issue_label='v5n1',
                journal='Historia Ciencias Saude',
                journal_acronym='hcs',
                collection_acronym='scl',
                publication_year=2026,
                xml_file_name='S0104-59702026000100003.xml',
                prefix='10.1590',
                doi='10.1590/S0104-59702026000100003',
                submission_status='error',
                feedback_status='failure',
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
            'publica',
        )

        self.assertEqual(
            [item.journal_acronym for item in query.all()],
            ['csp'],
        )

    def test_search_deposits_matches_submission_status(self):
        query, _ = search_deposits(
            self.session.query(Deposit),
            'waiti',
        )

        self.assertIn(
            'waiting',
            [item.submission_status for item in query.all()],
        )

    def test_search_deposits_matches_feedback_status(self):
        query, _ = search_deposits(
            self.session.query(Deposit),
            'succ',
        )

        self.assertEqual(
            [item.feedback_status for item in query.all()],
            ['success'],
        )

    def test_search_deposits_matches_status_variants(self):
        search_cases = {
            'fail': {'failure'},
            'notapp': {'notapplicable'},
            'err': {'error'},
        }

        for term, expected_statuses in search_cases.items():
            query, _ = search_deposits(
                self.session.query(Deposit),
                term,
            )

            result_statuses = {
                item.submission_status for item in query.all()
            } | {
                item.feedback_status for item in query.all()
            }

            self.assertTrue(
                expected_statuses.issubset(result_statuses),
                msg='term %s did not match expected statuses' % term,
            )

    def test_search_deposits_ignores_blank_input(self):
        query, search_term = search_deposits(
            self.session.query(Deposit),
            '   ',
        )

        self.assertEqual(search_term, '')
        self.assertEqual(query.count(), 4)

    def test_apply_deposit_sort_orders_by_submission_status(self):
        query, sort_key = apply_deposit_sort(
            self.session.query(Deposit),
            'submission_status_asc',
        )

        self.assertEqual(sort_key, 'submission_status_asc')
        self.assertEqual(
            [item.submission_status for item in query.all()],
            ['error', 'failure', 'notapplicable', 'waiting'],
        )

    def test_apply_deposit_sort_orders_by_feedback_status_desc(self):
        query, sort_key = apply_deposit_sort(
            self.session.query(Deposit),
            'feedback_status_desc',
        )

        self.assertEqual(sort_key, 'feedback_status_desc')
        self.assertEqual(
            [item.feedback_status for item in query.all()],
            ['waiting', 'success', 'failure', 'error'],
        )
