# coding: utf-8
"""
Crossref Client that implements some of the Publisher Crossref API endpoints to
request a DOI number and follow the request status.
"""
import requests


class CrossrefClient(object):

    def __init__(self, prefix, api_user, api_key, test_mode=False):

        self.prefix = prefix
        self.api_user = api_user
        self.api_key = api_key

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

        endpoint = "https://doi.crossref.org/servlet/deposit"

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

        endpoint = "https://doi.crossref.org/servlet/submissionDownload"

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

        endpoint = "https://doi.crossref.org/servlet/submissionDownload"

        params = {
            'usr': self.api_user,
            'pwd': self.api_key,
            'doi_batch_id': doi_batch_id,
            'type': data_type
        }

        result = self._do_http_request('get', endpoint, data=params, timeout=10)

        return result
