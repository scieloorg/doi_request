"""Leitura, validação e serialização do XML de depósito Crossref."""
from io import BytesIO

from celery.utils.log import get_task_logger
from lxml import etree
import xmlschema

from tasks.settings import (
    CROSSREF_DEPOSITOR_EMAIL,
    CROSSREF_DEPOSITOR_NAME,
    CROSSREF_SCHEMA_NAMESPACE,
    CROSSREF_SCHEMA_VERSION,
    CROSSREF_XSD_PATH,
)


logger = get_task_logger(__name__)


def _parse_schema():
    try:
        return xmlschema.XMLSchema11(CROSSREF_XSD_PATH)
    except Exception:
        logger.exception(
            'Fail to parse Crossref schema at "%s"', CROSSREF_XSD_PATH
        )
        raise


PARSED_SCHEMA = _parse_schema()


def _crossref_tag(name):
    return '{%s}%s' % (CROSSREF_SCHEMA_NAMESPACE, name)


def _required_element(xml_doc, path):
    element = xml_doc.find(path)
    if element is None:
        raise ValueError(
            'Required Crossref %s element not found: %s' % (
                CROSSREF_SCHEMA_VERSION, path
            )
        )
    return element


def setup_depositor(xml_doc, doi, depositor_name=None, depositor_email=None):
    depositor_name = depositor_name or CROSSREF_DEPOSITOR_NAME
    depositor_email = depositor_email or CROSSREF_DEPOSITOR_EMAIL

    _required_element(
        xml_doc, './/' + _crossref_tag('registrant')
    ).text = depositor_name
    _required_element(
        xml_doc, './/' + _crossref_tag('depositor_name')
    ).text = depositor_name
    _required_element(
        xml_doc, './/' + _crossref_tag('email_address')
    ).text = depositor_email
    _required_element(
        xml_doc,
        './/%s/%s' % (_crossref_tag('doi_data'), _crossref_tag('doi'))
    ).text = doi

    return xml_doc


def get_doi_batch_id(xml_doc):
    return _required_element(
        xml_doc, './/' + _crossref_tag('doi_batch_id')
    ).text


def serialize_xml(xml_doc):
    return etree.tostring(
        xml_doc,
        encoding='utf-8',
        pretty_print=True,
        xml_declaration=True
    ).decode('utf-8')


def parse_xml(xml):
    return etree.parse(BytesIO(xml.encode('utf-8')))


def xml_is_valid(xml, doi, only_front=False, schema=None,
                 depositor_name=None, depositor_email=None):
    if isinstance(xml, str):
        xml = xml.encode('utf-8')

    try:
        xml_doc = etree.parse(BytesIO(xml))
        logger.debug('XML is well formed')
    except Exception as exc:
        logger.exception(exc)
        logger.error('Fail to parse XML')
        return (False, None, str(exc))

    try:
        setup_depositor(
            xml_doc,
            doi,
            depositor_name=depositor_name,
            depositor_email=depositor_email
        )
    except ValueError as exc:
        logger.error(str(exc))
        return (False, xml_doc, str(exc))

    if only_front:
        citation_list = xml_doc.find(
            './/' + _crossref_tag('citation_list')
        )
        if citation_list is not None:
            citation_list.getparent().remove(citation_list)

    xml_doc_pprint = etree.tostring(xml_doc, pretty_print=True)
    xml_doc = etree.parse(BytesIO(xml_doc_pprint))
    validation_schema = schema or PARSED_SCHEMA
    errors = list(validation_schema.iter_errors(
        xml_doc_pprint.decode('utf-8')
    ))

    if errors:
        error_message = '\n'.join(str(error) for error in errors)
        logger.error('Crossref XML is invalid: %s', error_message)
        return (False, xml_doc, error_message)

    logger.debug('XML is valid')
    return (True, xml_doc, '')
