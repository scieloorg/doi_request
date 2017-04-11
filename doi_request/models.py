from datetime import datetime

from mongoengine import *

SUBMISSION_STATUS = (
    'waiting',
    'success',
    'error',
    'notapplicable'
    )

connect('doimanager', host='mongodb://127.0.0.1:27017/doimanager')


class DepositItem(DynamicDocument):

    # join of 3 letters collection acronym + PIF ex: scl_S0012-12192014000100005
    code = StringField(max_length=27, uninque=True, primary_key=True)

    pid = StringField(max_length=32, required=True)
    collection_acronym = StringField(max_length=23, required=True)
    xml_file_name = StringField(max_length=32, required=True)
    prefix = StringField(max_length=16)
    doi = StringField(max_length=32)
    doi_batch_id = StringField(max_length=32)
    xml_is_valid = BooleanField(default=False)
    submitted_xml = StringField()
    feedback_json = StringField()
    feedback_status = StringField(max_length=16)
    feddback_xml = StringField()
    submission_status = StringField(max_length=16, choices=SUBMISSION_STATUS)
    submission_status_code = IntField(max_length=3)
    submission_response = StringField()
    updated_at = DateTimeField(default=datetime.now)

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
