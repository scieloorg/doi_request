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
    doi = StringField(max_length=32)
    doi_batch_id = StringField(max_length=32)
    xml_is_valid = BooleanField(default=False)
    submitted_xml = StringField()
    feedback_json = StringField()
    feedback_status = StringField(max_length=16)
    feddback_xml = StringField()
    feedback_updated_at = DateTimeField()
    submission_status = StringField(max_length=16, choices=SUBMISSION_STATUS)
    submission_status_code = IntField(max_length=3)
    submission_updated_at = DateTimeField()
    submission_response = StringField()
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

        timeline = [
            (self.started_at, 'started', 'fa-info', 'gray', 'Iniciado processo de requisição de DOI e/ou atualização de metadados no Crossref.')
        ]

        if self.submission_status == 'notapplicable':
            return [
                (self.started_at, 'notapplicable', 'fa-info', 'gray', 'XML não enviado, provavelmente pelo Prefixo do DOI não estar vinculado ao prefixo desta coleção')
            ]

        submission = (self.submission_updated_at, self.submission_status, 'fa-industry', 'orange', 'Produzindo XML para envío')
        if self.feedback_status == 'waiting':
            submission = (self.submission_updated_at, self.submission_status, 'fa-spinner', 'orange', 'XML esta na fila de envío para Crossref')
        if self.submission_status == 'success':
            submission = (self.submission_updated_at, self.submission_status, 'fa-envelope', 'green', 'XML enviado para Crossref')
        elif self.submission_status == 'error':
            submission = (self.submission_updated_at, self.submission_status, 'fa-thumbs-down', 'red', 'XML não enviado ao Crossref, processo interrompido')
            return timeline.append(submission)
        timeline.append(submission)

        feedback = (self.feedback_updated_at, self.feedback_status, 'fa-spinner', 'orange', 'XML aguardando recebimento no Crossref')
        if self.feedback_status == 'waiting':
            feedback = (self.feedback_updated_at, self.feedback_status, 'fa-spinner', 'orange', 'XML recebido pelo crossref, em processo de avaliação')
        elif self.feedback_status == 'success':
            feedback = (self.submission_updated_at, self.feedback_status, 'fa-thumbs-up', 'green', 'DOI Registrado')
        elif self.feedback_status == 'error':
            feedback = (self.submission_updated_at, self.feedback_status, 'fa-thumbs-down', 'red', 'DOI não registrado, processo interrompido')
            return timeline.append(feedback)
        timeline.append(feedback)

        timeline.append(
            (self.updated_at, 'updated', 'fa-info', 'gray', 'Data da última atualização.')
        )

        return timeline
