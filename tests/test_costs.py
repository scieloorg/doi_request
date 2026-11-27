import unittest
from datetime import datetime

from doi_request.costs import (
    BACKFILE_COST,
    CURRENT_COST,
    calculate_cost,
    is_backfile,
    summarize_monthly_costs,
)


class CostCalculationTest(unittest.TestCase):

    def test_publication_before_limit_is_backfile(self):
        reference = datetime(2026, 6, 1)
        self.assertTrue(is_backfile(2023, reference))
        self.assertEqual(BACKFILE_COST, calculate_cost(2023, reference))

    def test_publication_from_limit_onward_is_current(self):
        reference = datetime(2026, 6, 1)
        self.assertFalse(is_backfile(2024, reference))
        self.assertEqual(CURRENT_COST, calculate_cost('2026', reference))

    def test_monthly_summary_splits_retro_and_new(self):
        month = datetime(2026, 3, 1)
        rows = [
            {'registry_month': month, 'retro': True, 'total': 0.30},
            {'registry_month': month, 'retro': False, 'total': 2},
        ]

        summary = summarize_monthly_costs(rows)

        self.assertEqual(
            {'retro': 0.30, 'new': 2, 'total': 2.30},
            summary['2026-03'],
        )


if __name__ == '__main__':
    unittest.main()
