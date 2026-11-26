import os
import unittest
from datetime import datetime
from io import BytesIO
from unittest import mock

from lxml import etree

from crossref import relations
from crossref.client import CrossrefLookupError
from doi_request.models import Base, PlainSession, transactional_session
from doi_request.models.depositor import Deposit, Expenses, LogEvent
from tasks import celery


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
ENGINE = PlainSession.kw['bind']


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding='utf-8') as fixture:
        return fixture.read()


def add_deposit(code, doi, xml, **fields):
    data = dict(
        code=code, pid=code, issn='1234-5678', journal='Journal',
        journal_acronym='jt', collection_acronym='scl',
        xml_file_name='%s.xml' % code, prefix='10.1590', doi=doi,
        publication_year=2026, submission_xml=xml,
        submission_status='waiting', started_at=datetime.now(),
        updated_at=datetime.now())
    data.update(fields)
    with transactional_session() as session:
        session.add(Deposit(**data))


def get_deposit(code):
    with transactional_session() as session:
        deposit = session.query(Deposit).filter_by(code=code).first()
        session.expunge(deposit)
        return deposit


def event_titles(code):
    with transactional_session() as session:
        return [
            event.title
            for event in session.query(LogEvent).filter_by(deposit_code=code)
        ]


def extracted_relations(xml):
    return relations.extract_doi_relations(
        etree.parse(BytesIO(xml.encode('utf-8'))))


def doi_xml(doi, relation_xml=''):
    xml = load_fixture('crossref_5_5_without_references.xml')
    return xml.replace(
        '<doi>10.1234/original-doi</doi>',
        '<doi>%s</doi>' % doi
    ).replace('<doi_data>', relation_xml + '<doi_data>', 1)


def related_item_xml(relationship_type, target_doi):
    return (
        '<program xmlns="http://www.crossref.org/relations.xsd" name="relations">'
        '<related_item><inter_work_relation relationship-type="%s" '
        'identifier-type="doi">%s</inter_work_relation></related_item>'
        '</program>' % (relationship_type, target_doi))


class RelationTaskTestCase(unittest.TestCase):

    def setUp(self):
        Base.metadata.drop_all(ENGINE)
        Base.metadata.create_all(ENGINE)
        patcher = mock.patch.object(celery, 'chain')
        self.chain = patcher.start()
        self.addCleanup(patcher.stop)


class LoadXmlFromArticlemetaTest(RelationTaskTestCase):

    def test_keeps_batch_head_from_articlemeta(self):
        xml = load_fixture('crossref_5_5_without_references.xml')
        add_deposit('scl_S1', '10.1590/original', xml)

        with mock.patch.object(celery, 'ThriftClient') as thrift:
            thrift.return_value.document.return_value = xml
            self.assertEqual(
                'scl_S1', celery.load_xml_from_articlemeta('scl_S1'))

        deposit = get_deposit('scl_S1')
        xml_doc = etree.parse(
            BytesIO(deposit.submission_xml.encode('utf-8')))

        self.assertEqual(
            'test-batch-no-refs', celery.get_doi_batch_id(xml_doc))


class PrepareDocumentTest(RelationTaskTestCase):

    def test_renews_timestamp_and_keeps_batch_id(self):
        xml = load_fixture('crossref_5_5_without_references.xml')
        add_deposit('scl_S1', '10.1590/original', xml)

        self.assertEqual('scl_S1', celery.prepare_document('scl_S1'))

        deposit = get_deposit('scl_S1')
        xml_doc = etree.parse(
            BytesIO(deposit.submission_xml.encode('utf-8')))
        timestamp = xml_doc.findtext(
            './/{%s}timestamp' % celery.CROSSREF_SCHEMA_NAMESPACE)

        self.assertEqual('test-batch-no-refs', deposit.doi_batch_id)
        self.assertEqual(
            deposit.doi_batch_id, celery.get_doi_batch_id(xml_doc))
        self.assertEqual(17, len(timestamp))
        self.assertTrue(timestamp.isdigit())
        self.assertNotEqual('20260908120001', timestamp)


class ResolveRelationsTest(RelationTaskTestCase):

    def setUp(self):
        super(ResolveRelationsTest, self).setUp()
        lookup = mock.patch.object(celery.crossref_client, 'is_doi_registered')
        self.is_doi_registered = lookup.start()
        self.addCleanup(lookup.stop)
        thrift = mock.patch.object(celery, 'ThriftClient')
        self.articlemeta = thrift.start().return_value
        self.addCleanup(thrift.stop)
        enqueue = mock.patch.object(
            celery.registry_dispatcher_document_skip_deposited, 'delay')
        self.enqueue_principal = enqueue.start()
        self.addCleanup(enqueue.stop)

    def test_strips_only_unregistered_deferred_relations(self):
        registered = {'10.1590/commented', '10.1590/corrected-article'}
        self.is_doi_registered.side_effect = lambda doi: doi in registered
        add_deposit(
            'scl_S1', '10.1590/original',
            load_fixture('crossref_5_5_with_relations.xml'))

        self.assertEqual('scl_S1', celery.resolve_relations('scl_S1'))

        submitted = extracted_relations(get_deposit('scl_S1').submission_xml)
        self.assertEqual(
            ['10.1590/commented', '10.1590/corrected-article'],
            sorted(relation.target_doi for relation in submitted))
        self.assertEqual(5, self.is_doi_registered.call_count)
        self.enqueue_principal.assert_not_called()
        titles = event_titles('scl_S1')
        self.assertIn(
            'Found 5 related DOI relations in the document', titles)
        self.assertIn(
            'Relation found: 10.1590/original --hasTranslation--> '
            '10.1590/translation [related_item]',
            titles)
        self.assertIn(
            'Related DOI 10.1590/translation is not registered in Crossref',
            titles)
        self.assertIn(
            'Relation deferred from the first submission: '
            '10.1590/original --hasTranslation--> '
            '10.1590/translation [related_item]',
            titles)

    def test_blocked_deposit_retries_and_enqueues_principal(self):
        self.is_doi_registered.return_value = False
        self.articlemeta.document.return_value = mock.Mock(publisher_id='S2')
        add_deposit(
            'scl_S1', '10.1590/comment',
            doi_xml('10.1590/comment',
                    related_item_xml('isCommentOn', '10.1590/principal')))

        with self.assertRaises(celery.ChainAborted):
            celery.resolve_relations('scl_S1')

        self.assertEqual('blocked', get_deposit('scl_S1').submission_status)
        self.articlemeta.document.assert_called_once_with(
            '10.1590/PRINCIPAL', 'scl')
        self.enqueue_principal.assert_called_once_with('S2', 'scl')

    def test_existing_principal_is_not_enqueued(self):
        self.is_doi_registered.return_value = False
        add_deposit(
            'scl_S2', '10.1590/principal', doi_xml('10.1590/principal'))
        add_deposit(
            'scl_S1', '10.1590/comment',
            doi_xml('10.1590/comment',
                    related_item_xml('isCommentOn', '10.1590/principal')))

        with self.assertRaises(celery.ChainAborted):
            celery.resolve_relations('scl_S1')

        self.articlemeta.document.assert_not_called()
        self.enqueue_principal.assert_not_called()

    def test_missing_principal_marks_deposit_as_error(self):
        self.is_doi_registered.return_value = False
        self.articlemeta.document.return_value = None
        add_deposit(
            'scl_S1', '10.1590/comment',
            doi_xml('10.1590/comment',
                    related_item_xml('isCommentOn', '10.1590/principal')))

        with self.assertRaises(celery.RelatedDocumentNotFound):
            celery.resolve_relations('scl_S1')

        self.assertEqual('error', get_deposit('scl_S1').submission_status)

    def test_detects_cycle_from_existing_xml(self):
        self.is_doi_registered.return_value = False
        add_deposit(
            'scl_S2', '10.1590/principal',
            doi_xml('10.1590/principal',
                    related_item_xml('isCommentOn', '10.1590/comment')),
            submission_status='blocked')
        add_deposit(
            'scl_S1', '10.1590/comment',
            doi_xml('10.1590/comment',
                    related_item_xml('isCommentOn', '10.1590/principal')))

        with self.assertRaises(celery.RelationCycleError):
            celery.resolve_relations('scl_S1')

        self.assertEqual('error', get_deposit('scl_S1').submission_status)

    def test_crossref_failure_does_not_change_submission_xml(self):
        xml = load_fixture('crossref_5_5_with_relations.xml')
        self.is_doi_registered.side_effect = CrossrefLookupError(
            '10.1590/commented', 500)
        add_deposit('scl_S1', '10.1590/original', xml)

        with self.assertRaises(CrossrefLookupError):
            celery.resolve_relations('scl_S1')

        self.assertEqual(xml, get_deposit('scl_S1').submission_xml)


class FinalizeRelationsTest(RelationTaskTestCase):

    def setUp(self):
        super(FinalizeRelationsTest, self).setUp()
        thrift = mock.patch.object(celery, 'ThriftClient')
        self.articlemeta = thrift.start().return_value
        self.addCleanup(thrift.stop)
        lookup = mock.patch.object(celery.crossref_client, 'is_doi_registered')
        self.is_doi_registered = lookup.start()
        self.addCleanup(lookup.stop)

    def _add_initial_success(self):
        original = load_fixture('crossref_5_5_with_relations.xml')
        submitted_doc = etree.parse(BytesIO(original.encode('utf-8')))
        relations.strip_relations(
            submitted_doc,
            {'10.1590/translation', '10.1590/original', '10.1590/review'})
        add_deposit(
            'scl_S1', '10.1590/original',
            celery.serialize_xml(submitted_doc),
            feedback_status='success', doi_batch_id='initial-batch')
        self.articlemeta.document.return_value = original
        return original

    def test_prepares_final_deposit_once_when_targets_are_registered(self):
        self._add_initial_success()
        self.is_doi_registered.return_value = True

        self.assertEqual('scl_S1', celery.finalize_relations('scl_S1'))
        self.assertEqual('scl_S1', celery.finalize_relations('scl_S1'))

        deposit = get_deposit('scl_S1')
        self.assertEqual('waiting', deposit.feedback_status)
        self.assertEqual('waiting', deposit.submission_status)
        self.assertEqual('initial-batch', deposit.doi_batch_id)
        self.assertEqual(5, len(extracted_relations(deposit.submission_xml)))
        self.chain.assert_called_once()
        self.chain.return_value.delay.assert_called_once_with('scl_S1')

    def test_retries_without_changing_xml_while_target_is_pending(self):
        self._add_initial_success()
        self.is_doi_registered.return_value = False
        before = get_deposit('scl_S1').submission_xml

        with self.assertRaises(celery.ChainAborted):
            celery.finalize_relations('scl_S1')

        deposit = get_deposit('scl_S1')
        self.assertEqual(before, deposit.submission_xml)
        self.assertEqual('success', deposit.feedback_status)
        self.chain.assert_not_called()

    def test_skips_final_deposit_when_first_xml_kept_every_relation(self):
        original = load_fixture('crossref_5_5_with_relations.xml')
        add_deposit(
            'scl_S1', '10.1590/original', original,
            feedback_status='success', doi_batch_id='initial-batch')
        self.articlemeta.document.return_value = original

        self.assertEqual('scl_S1', celery.finalize_relations('scl_S1'))

        self.is_doi_registered.assert_not_called()
        self.chain.assert_not_called()


class RequestDoiStatusHelpersTest(RelationTaskTestCase):

    def test_batch_feedback_requires_every_record_success(self):
        xml_doc = etree.fromstring(
            '<doi_batch_diagnostic status="completed">'
            '<record_diagnostic status="Success"><doi>10.1590/a</doi>'
            '<msg>Successfully added</msg></record_diagnostic>'
            '<record_diagnostic status="Failure"><doi>10.1590/b</doi>'
            '<msg>Relation target not found</msg></record_diagnostic>'
            '</doi_batch_diagnostic>').getroottree()

        status, body = celery.batch_feedback(xml_doc)

        self.assertEqual('failure', status)
        self.assertEqual(
            '10.1590/a: Successfully added\n'
            '10.1590/b: Relation target not found',
            body)

    def test_batch_feedback_without_records_is_unknown(self):
        xml_doc = etree.fromstring(
            '<doi_batch_diagnostic status="completed"/>').getroottree()
        status, body = celery.batch_feedback(xml_doc)
        self.assertEqual('unknow', status)
        self.assertEqual('', body)

    def test_register_expenses_is_idempotent(self):
        add_deposit(
            'scl_S1', '10.1590/original', doi_xml('10.1590/original'))

        for _ in range(2):
            with transactional_session() as session:
                deposit = session.query(Deposit).filter_by(
                    code='scl_S1').first()
                celery.register_expenses(session, deposit)

        with transactional_session() as session:
            self.assertEqual(
                1,
                session.query(Expenses).filter_by(
                    doi='10.1590/original').count())


class SchemaCompatibilityTest(unittest.TestCase):

    def test_relations_do_not_extend_historical_schema(self):
        self.assertNotIn('depositrelation', Base.metadata.tables)
        deposit_columns = set(Base.metadata.tables['deposit'].columns.keys())
        self.assertNotIn('original_xml', deposit_columns)
        self.assertNotIn('relations_stage', deposit_columns)


if __name__ == '__main__':
    unittest.main()
