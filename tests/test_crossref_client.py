import unittest
from unittest import mock

from crossref.client import CrossrefClient, CrossrefLookupError


class IsDoiRegisteredTest(unittest.TestCase):

    def setUp(self):
        self.client = CrossrefClient('10.1590', 'user', 'password')

    @mock.patch('crossref.client.requests.get')
    def test_registered(self, get):
        get.return_value = mock.Mock(status_code=200)

        self.assertTrue(self.client.is_doi_registered('10.1590/x'))
        get.assert_called_once_with(
            'https://api.crossref.org/works/10.1590/x/agency', params=None, timeout=10)

    @mock.patch('crossref.client.requests.get')
    def test_not_registered(self, get):
        get.return_value = mock.Mock(status_code=404)

        self.assertFalse(self.client.is_doi_registered('10.1590/x'))

    @mock.patch('crossref.client.requests.get')
    def test_unexpected_status_raises(self, get):
        get.return_value = mock.Mock(status_code=500)

        with self.assertRaises(CrossrefLookupError) as raised:
            self.client.is_doi_registered('10.1590/x')

        self.assertEqual(500, raised.exception.status_code)
        self.assertEqual('10.1590/x', raised.exception.doi)


class CustomEndpointsTest(unittest.TestCase):

    def setUp(self):
        self.client = CrossrefClient(
            '10.1590', 'user', 'password',
            deposit_url='http://crossref_mock:8000/',
            api_url='http://crossref_mock:8000')

    @mock.patch('crossref.client.requests.post')
    def test_register_doi(self, post):
        self.client.register_doi('scl_S0001', '<doi_batch/>')

        self.assertEqual(
            'http://crossref_mock:8000/servlet/deposit', post.call_args[0][0])

    @mock.patch('crossref.client.requests.get')
    def test_request_doi_status(self, get):
        self.client.request_doi_status_by_batch_id('batch-1')

        self.assertEqual(
            'http://crossref_mock:8000/servlet/submissionDownload',
            get.call_args[0][0])

    @mock.patch('crossref.client.requests.get')
    def test_is_doi_registered(self, get):
        get.return_value = mock.Mock(status_code=200)

        self.client.is_doi_registered('10.1590/x')

        get.assert_called_once_with(
            'http://crossref_mock:8000/works/10.1590/x/agency', params=None, timeout=10)


if __name__ == '__main__':
    unittest.main()
