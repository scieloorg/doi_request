import os
import unittest
from datetime import datetime
from io import BytesIO

from lxml import etree

from crossref import relations
from tasks import celery


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
NS = {
    'cr': 'http://www.crossref.org/schema/5.5.0',
    'rel': relations.RELATIONS_NAMESPACE,
    'ai': 'http://www.crossref.org/AccessIndicators.xsd',
}


def load_xml_doc():
    path = os.path.join(FIXTURES_DIR, 'crossref_5_5_with_relations.xml')
    with open(path, 'rb') as fixture:
        return etree.parse(BytesIO(fixture.read()))


def assert_valid(test_case, xml_doc):
    is_valid, _, error = celery.xml_is_valid(
        celery.serialize_xml(xml_doc), '10.1590/original',
        depositor_name='Test Depositor',
        depositor_email='depositor@example.org')
    test_case.assertTrue(is_valid, error)


def target_dois(xml_doc):
    return sorted(relation.target_doi for relation in relations.extract_doi_relations(xml_doc))


class ExtractRelationsTest(unittest.TestCase):

    def test_fixture_is_valid(self):
        assert_valid(self, load_xml_doc())

    def test_submission_dois(self):
        self.assertEqual(
            ['10.1590/original', '10.1590/translation'],
            relations.submission_dois(load_xml_doc()))

    def test_extracts_doi_relations_with_source_and_normalized_target(self):
        self.assertEqual([
            relations.Relation('10.1590/original', '10.1590/translation', relations.RELATED_ITEM, 'hasTranslation'),
            relations.Relation('10.1590/original', '10.1590/commented', relations.RELATED_ITEM, 'isCommentOn'),
            relations.Relation('10.1590/original', '10.1590/review', relations.RELATED_ITEM, 'hasReview'),
            relations.Relation('10.1590/original', '10.1590/corrected-article', relations.CROSSMARK_UPDATE, 'correction'),
            relations.Relation('10.1590/translation', '10.1590/original', relations.RELATED_ITEM, 'isTranslationOf'),
        ], relations.extract_doi_relations(load_xml_doc()))

    def test_relation_role(self):
        xml_doc = load_xml_doc()
        own_dois = set(relations.submission_dois(xml_doc))

        roles = dict(
            ((relation.relationship_type, relation.target_doi),
             relations.relation_role(relation, own_dois))
            for relation in relations.extract_doi_relations(xml_doc))

        self.assertEqual({
            ('hasTranslation', '10.1590/translation'): relations.DEFERRED,
            ('isCommentOn', '10.1590/commented'): relations.BLOCKING,
            ('hasReview', '10.1590/review'): relations.DEFERRED,
            ('correction', '10.1590/corrected-article'): relations.BLOCKING,
            ('isTranslationOf', '10.1590/original'): relations.DEFERRED,
        }, roles)


class StripRelationsTest(unittest.TestCase):

    def test_strips_only_given_targets_and_empty_programs(self):
        xml_doc = load_xml_doc()

        removed = relations.strip_relations(
            xml_doc, ['10.1590/translation', '10.1590/original', '10.1590/review'])

        self.assertEqual(
            ['10.1590/translation', '10.1590/review', '10.1590/original'],
            [relation.target_doi for relation in removed])
        self.assertEqual(
            ['10.1590/commented', '10.1590/corrected-article'],
            target_dois(xml_doc))
        self.assertEqual(1, len(xml_doc.findall('.//rel:program', NS)))
        self.assertEqual(
            'https://example.org/dataset',
            xml_doc.findtext('.//rel:inter_work_relation[@identifier-type="uri"]', namespaces=NS))
        assert_valid(self, xml_doc)

    def test_strips_crossmark_update_keeping_custom_metadata(self):
        xml_doc = load_xml_doc()

        relations.strip_relations(xml_doc, ['10.1590/corrected-article'])

        self.assertIsNone(xml_doc.find('.//cr:updates', NS))
        self.assertIsNotNone(xml_doc.find('.//cr:crossmark/cr:custom_metadata/ai:program', NS))
        assert_valid(self, xml_doc)

    def test_strips_every_doi_relation(self):
        xml_doc = load_xml_doc()

        relations.strip_relations(
            xml_doc, [relation.target_doi for relation in relations.extract_doi_relations(xml_doc)])

        self.assertEqual([], relations.extract_doi_relations(xml_doc))
        assert_valid(self, xml_doc)

    def test_without_targets_keeps_xml_untouched(self):
        xml_doc = load_xml_doc()
        before = etree.tostring(xml_doc)

        self.assertEqual([], relations.strip_relations(xml_doc, []))
        self.assertEqual(before, etree.tostring(xml_doc))


class BatchHeadTest(unittest.TestCase):

    def test_renews_timestamp_and_keeps_batch_id(self):
        moment = datetime(2026, 11, 18, 17, 30, 5, 123456)
        xml_doc = relations.set_batch_head(load_xml_doc(), moment)

        self.assertEqual('test-batch-relations', celery.get_doi_batch_id(xml_doc))
        self.assertEqual('20261118173005123', xml_doc.findtext('.//cr:timestamp', namespaces=NS))
        assert_valid(self, xml_doc)


if __name__ == '__main__':
    unittest.main()
