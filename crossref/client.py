# coding: utf-8
"""
Crossref Client that implements some of the Publisher Crossref API endpoints to
request a DOI number and follow the request status.
"""
import requests


class CrossrefLookupError(Exception):

    def __init__(self, doi, status_code):
        self.doi = doi
        self.status_code = status_code
        super(CrossrefLookupError, self).__init__(
            'Unexpected HTTP status %d checking DOI (%s) in Crossref' % (
                status_code, doi))


class CrossrefClient(object):

    def __init__(self, prefix, api_user, api_key, deposit_url, api_url):

        self.prefix = prefix
        self.api_user = api_user
        self.api_key = api_key
        self.deposit_url = deposit_url.rstrip('/')
        self.api_url = api_url.rstrip('/')

    def _do_http_request(self, method, endpoint, data=None, files=None, timeout=10):

        if method == 'post':
            action = requests.post
        else:
            action = requests.get

        if method == 'post':
            result = action(endpoint, data=data, files=files, timeout=timeout)
        else:
            result = action(endpoint, params=data, timeout=timeout)

        return result

    def register_doi(self, submission_id, request_xml):
        """
        This method registry a new DOI number in Crossref or update some DOI
        metadata.

        submission_id: Will be used as the submission file name. The file name
        could be used in future requests to retrieve the submission status.

        request_xml: The XML with the document metadata. It must be under
        compliance with the Crossref Submission Schema.
        """

        endpoint = "%s/servlet/deposit" % self.deposit_url

        files = {
            'mdFile': ('%s.xml' % submission_id, request_xml)
        }

        params = {
            'operation': 'doMDUpload',
            'login_id': self.api_user,
            'login_passwd': self.api_key
        }

        result = self._do_http_request(
            'post', endpoint, data=params, files=files, timeout=10)

        return result

    def request_doi_status_by_filename(self, file_name, data_type='result'):
        """
        This method retrieve the DOI requests status.

        file_name: Used as unique ID to identify a deposit.

        data_type: [contents, result]
            contents - retrieve the XML submited by the publisher
            result - retrieve a JSON with the status of the submission
        """

        endpoint = "%s/servlet/submissionDownload" % self.deposit_url

        params = {
            'usr': self.api_user,
            'pwd': self.api_key,
            'file_name': file_name,
            'type': data_type
        }

        result = self._do_http_request('get', endpoint, data=params, timeout=10)

        return result

    def request_doi_status_by_batch_id(self, doi_batch_id, data_type='result'):
        """
        This method retrieve the DOI requests status.

        file_name: Used as unique ID to identify a deposit.

        data_type: [contents, result]
            contents - retrieve the XML submited by the publisher
            result - retrieve a XML with the status of the submission
        """

        endpoint = "%s/servlet/submissionDownload" % self.deposit_url

        params = {
            'usr': self.api_user,
            'pwd': self.api_key,
            'doi_batch_id': doi_batch_id,
            'type': data_type
        }

        result = self._do_http_request('get', endpoint, data=params, timeout=10)

        return result

    def is_doi_registered(self, doi):
        """
        Check in the Crossref REST API whether the DOI is registered.

        Raises CrossrefLookupError when Crossref answers with an unexpected
        HTTP status, so the caller never treats an unknown state as absent.
        """

        endpoint = "%s/works/%s/agency" % (self.api_url, doi)

        result = self._do_http_request('get', endpoint, timeout=10)

        if result.status_code == 200:
            return True

        if result.status_code == 404:
            return False

        raise CrossrefLookupError(doi, result.status_code)
