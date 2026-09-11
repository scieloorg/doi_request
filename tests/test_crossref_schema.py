import os
import unittest

from tasks import celery


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
TEST_DOI = '10.1234/updated-doi'
TEST_DEPOSITOR_NAME = 'Test Depositor'
TEST_DEPOSITOR_EMAIL = 'depositor@example.org'


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name), encoding='utf-8') as fixture:
        return fixture.read()


def validate(xml, only_front=False):
    return celery.xml_is_valid(
        xml,
        TEST_DOI,
        only_front=only_front,
        depositor_name=TEST_DEPOSITOR_NAME,
        depositor_email=TEST_DEPOSITOR_EMAIL
    )


class CrossrefSchemaTest(unittest.TestCase):

    def test_compiles_crossref_5_5_as_xsd_1_1(self):
        self.assertEqual('XMLSchema11', celery.PARSED_SCHEMA.__class__.__name__)
        self.assertTrue(
            celery.CROSSREF_XSD_PATH.endswith('crossref5.5.0.xsd')
        )

    def test_accepts_crossref_5_5_with_references(self):
        is_valid, xml_doc, error = validate(
            load_fixture('crossref_5_5_with_references.xml')
        )

        self.assertTrue(is_valid, error)
        self.assertIsNotNone(xml_doc)

    def test_accepts_crossref_5_5_without_references(self):
        is_valid, xml_doc, error = validate(
            load_fixture('crossref_5_5_without_references.xml')
        )

        self.assertTrue(is_valid, error)
        self.assertIsNotNone(xml_doc)

    def test_sets_depositor_doi_and_batch_id(self):
        is_valid, xml_doc, error = validate(
            load_fixture('crossref_5_5_without_references.xml')
        )

        self.assertTrue(is_valid, error)
        self.assertEqual(
            TEST_DEPOSITOR_NAME,
            xml_doc.find(
                './/' + celery._crossref_tag('registrant')
            ).text
        )
        self.assertEqual(
            TEST_DEPOSITOR_NAME,
            xml_doc.find(
                './/' + celery._crossref_tag('depositor_name')
            ).text
        )
        self.assertEqual(
            TEST_DEPOSITOR_EMAIL,
            xml_doc.find(
                './/' + celery._crossref_tag('email_address')
            ).text
        )
        self.assertEqual(
            TEST_DOI,
            xml_doc.find(
                './/%s/%s' % (
                    celery._crossref_tag('doi_data'),
                    celery._crossref_tag('doi')
                )
            ).text
        )
        self.assertEqual(
            'test-batch-no-refs', celery.get_doi_batch_id(xml_doc)
        )

    def test_removes_invalid_references_before_revalidating(self):
        xml = load_fixture('crossref_5_5_invalid_references.xml')

        is_valid, xml_doc, error = validate(xml)
        self.assertFalse(is_valid)
        self.assertIsNotNone(xml_doc)
        self.assertTrue(error)

        is_valid, xml_doc, error = validate(xml, only_front=True)
        self.assertTrue(is_valid, error)
        self.assertIsNone(
            xml_doc.find('.//' + celery._crossref_tag('citation_list'))
        )

    def test_rejects_crossref_4_4_namespace(self):
        xml = load_fixture('crossref_5_5_without_references.xml')
        xml = xml.replace(
            'http://www.crossref.org/schema/5.5.0',
            'http://www.crossref.org/schema/4.4.0'
        ).replace('version="5.5.0"', 'version="4.4.0"')

        is_valid, xml_doc, error = validate(xml)

        self.assertFalse(is_valid)
        self.assertIsNotNone(xml_doc)
        self.assertIn('Required Crossref 5.5.0 element not found', error)

    def test_rejects_crossref_4_4_version(self):
        xml = load_fixture('crossref_5_5_without_references.xml')
        xml = xml.replace('version="5.5.0"', 'version="4.4.0"')

        is_valid, xml_doc, error = validate(xml)

        self.assertFalse(is_valid)
        self.assertIsNotNone(xml_doc)
        self.assertIn("fixed value '5.5.0'", error)

    def test_reports_missing_required_element(self):
        xml = load_fixture('crossref_5_5_without_references.xml')
        xml = xml.replace(
            '<registrant>Original Registrant</registrant>', ''
        )

        is_valid, xml_doc, error = validate(xml)

        self.assertFalse(is_valid)
        self.assertIsNotNone(xml_doc)
        self.assertIn('registrant', error)


if __name__ == '__main__':
    unittest.main()
