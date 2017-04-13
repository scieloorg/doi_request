from datetime import datetime

from mongoengine import *

SUBMISSION_STATUS = (
    'waiting',
    'success',
    'error',
    'notapplicable'
    )

connect('doimanager', host='mongodb://mongo:27017/doimanager')


class DepositItem(DynamicDocument):

    # join of 3 letters collection acronym + PIF ex: scl_S0012-12192014000100005
    code = StringField(max_length=27, uninque=True, primary_key=True)

    pid = StringField(max_length=32, required=True)
    collection_acronym = StringField(max_length=23, required=True)
    xml_file_name = StringField(max_length=32, required=True)
    prefix = StringField(max_length=16)
    doi = StringField(max_length=128)
    doi_batch_id = StringField(max_length=32)
    xml_is_valid = BooleanField(default=False)
    deposit_xml = StringField(defaulf='')
    feedback_status = StringField(max_length=16)
    feedback_xml = StringField(defaulf='')
    feedback_log = StringField(defaulf='')
    feedback_updated_at = DateTimeField()
    feedback_request_status_code = IntField(max_length=3)
    submission_status = StringField(max_length=16, choices=SUBMISSION_STATUS)
    submission_status_code = IntField(max_length=3)
    submission_updated_at = DateTimeField()
    submission_response = StringField(defaulf='')
    submission_log = StringField(defaulf='')
    updated_at = DateTimeField(default=datetime.now)
    started_at = DateTimeField(default=datetime.now)

    meta = {
        'indexes': [
            'code',
            'prefix',
            'doi',
            'pid',
            'doi_batch_id',
            'updated_at',
            'submission_status',
            'feedback_status'
        ]
    }

    @property
    def timeline(self):

        if self.submission_status == 'notapplicable':
            return [
                (self.started_at, 'notapplicable', 'fa-info', 'gray', self.submission_log)
            ]

        timeline = []
        submission = (self.submission_updated_at, self.submission_status, 'fa-industry', 'orange', self.submission_log)
        if self.feedback_status == 'waiting':
            submission = (self.submission_updated_at, self.submission_status, 'fa-spinner', 'orange', self.submission_log)
        if self.submission_status == 'success':
            submission = (self.submission_updated_at, self.submission_status, 'fa-envelope', 'green', self.submission_log)
        elif self.submission_status == 'error':
            submission = (self.submission_updated_at, self.submission_status, 'fa-thumbs-down', 'red', self.submission_log)
        timeline.append(submission)

        feedback = None
        if self.feedback_status == 'waiting':
            feedback = (self.feedback_updated_at, self.feedback_status, 'fa-spinner', 'orange', self.feedback_log)
        elif self.feedback_status == 'success':
            feedback = (self.submission_updated_at, self.feedback_status, 'fa-thumbs-up', 'green', self.feedback_log)
        elif self.feedback_status == 'error':
            feedback = (self.submission_updated_at, self.feedback_status, 'fa-thumbs-down', 'red', self.feedback_log)

        if feedback:
            timeline.append(feedback)

        return timeline
