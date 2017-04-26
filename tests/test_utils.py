import unittest

from doi_request.utils import pagination_ruler


class UtilsTest(unittest.TestCase):

    def setUp(self):
        self.limit = 100
        self.total = 721
        self.display_pages = 5
        self.maxDiff = None

    @unittest.skip('Skip this test')
    def test_pagination_ruler_1(self):

        result = pagination_ruler(
            self.limit, self.total, 300
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (2, False, 100, 101, 200),
            (3, False, 200, 201, 300),
            (4, True, 300, 301, 400),
            (5, False, 400, 401, 500),
            (6, False, 500, 501, 600)
        ]

        self.assertEqual(result, expected)

    @unittest.skip('Skip this test')
    def test_pagination_ruler_2(self):

        result = pagination_ruler(
            self.limit, self.total, 200
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (1, False, 0, 1, 100),
            (2, False, 100, 101, 200),
            (3, True, 200, 201, 300),
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500)
        ]

        self.assertEqual(result, expected)

    @unittest.skip('Skip this test')
    def test_pagination_ruler_3_bondary_bottom_1(self):
        result = pagination_ruler(
            self.limit, self.total, 100
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (1, False, 0, 1, 100),
            (2, True, 100, 101, 200),
            (3, False, 200, 201, 300),
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500)
        ]

        self.assertEqual(result, expected)

    @unittest.skip('Skip this test')
    def test_pagination_ruler_3_bondary_bottom_2(self):
        result = pagination_ruler(
            self.limit, self.total, 0
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (1, True, 0, 1, 100),
            (2, False, 100, 101, 200),
            (3, False, 200, 201, 300),
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500)
        ]

        self.assertEqual(result, expected)

    @unittest.skip('Skip this test')
    def test_pagination_ruler_4(self):
        result = pagination_ruler(
            self.limit, self.total, 400
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (3, False, 200, 201, 300),
            (4, False, 300, 301, 400),
            (5, True, 400, 401, 500),
            (6, False, 500, 501, 600),
            (7, False, 600, 601, 700)
        ]

        self.assertEqual(result, expected)

    @unittest.skip('Skip this test')
    def test_pagination_ruler_5(self):
        result = pagination_ruler(
            self.limit, self.total, 500
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500),
            (6, True, 500, 501, 600),
            (7, False, 600, 601, 700),
            (8, False, 700, 701, 721)
        ]

        self.assertEqual(result, expected)

    def test_pagination_ruler_6_bondary_upper_1(self):
        result = pagination_ruler(
            self.limit, self.total, 600
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500),
            (6, False, 500, 501, 600),
            (7, True, 600, 601, 700),
            (8, False, 700, 701, 721)
        ]

        self.assertEqual(result, expected)

    def test_pagination_ruler_6_bondary_upper_7(self):
        result = pagination_ruler(
            self.limit, self.total, 700
        )

        # ["page, current, offset, start_range, end_range"]
        expected = [
            (4, False, 300, 301, 400),
            (5, False, 400, 401, 500),
            (6, False, 500, 501, 600),
            (7, False, 600, 601, 700),
            (8, True, 700, 701, 721)
        ]

        self.assertEqual(result, expected)
