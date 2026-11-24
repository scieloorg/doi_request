"""
Identificação e manipulação das relações por DOI presentes em um lote de
depósito Crossref (``rel:program/related_item`` e ``crossmark/updates/update``).
"""
from collections import namedtuple

from lxml import etree


RELATIONS_NAMESPACE = 'http://www.crossref.org/relations.xsd'

RELATED_ITEM = 'related_item'
CROSSMARK_UPDATE = 'crossmark_update'

BLOCKING = 'blocking'
DEFERRED = 'deferred'

# O documento corrente depende do alvo: o alvo precisa estar registrado antes.
BLOCKING_RELATIONSHIP_TYPES = frozenset([
    'isTranslationOf',
    'isCommentOn',
    'isReplyTo',
    'isReviewOf',
    'hasPreprint',
])

Relation = namedtuple(
    'Relation', 'source_doi target_doi element relationship_type')


def _crossref_namespace(xml_doc):
    return etree.QName(xml_doc.getroot()).namespace


def _crossref_tag(xml_doc, name):
    return '{%s}%s' % (_crossref_namespace(xml_doc), name)


def _relations_tag(name):
    return '{%s}%s' % (RELATIONS_NAMESPACE, name)


def _journal_article_doi(xml_doc, journal_article):
    doi_data_tag = _crossref_tag(xml_doc, 'doi_data')
    doi_tag = _crossref_tag(xml_doc, 'doi')
    doi = journal_article.find('%s/%s' % (doi_data_tag, doi_tag))
    return doi.text


def _relation_nodes(xml_doc):
    """Gera ``(nó removível, Relation)`` para cada relação por DOI do lote."""
    for journal_article in xml_doc.iter(_crossref_tag(xml_doc, 'journal_article')):
        source_doi = _journal_article_doi(xml_doc, journal_article)

        for related_item in journal_article.iter(_relations_tag('related_item')):
            # O schema exige inter_work_relation ou intra_work_relation como último filho.
            relation = related_item[-1]
            if relation.get('identifier-type') != 'doi':
                continue
            yield related_item, Relation(
                source_doi,
                relation.text,
                RELATED_ITEM,
                relation.get('relationship-type'),
            )

        for update in journal_article.iter(_crossref_tag(xml_doc, 'update')):
            yield update, Relation(
                source_doi,
                update.text,
                CROSSMARK_UPDATE,
                update.get('type'),
            )


def submission_dois(xml_doc):
    """
    Pega todos os DOI do xml
    """
    journal_article_tag = _crossref_tag(xml_doc, 'journal_article')
    dois = []
    for journal_article in xml_doc.iter(journal_article_tag):
        dois.append(_journal_article_doi(xml_doc, journal_article))
    return dois


def extract_doi_relations(xml_doc):
    return [relation for _, relation in _relation_nodes(xml_doc)]


def relation_role(relation, own_dois):
    if relation.target_doi in own_dois:
        return DEFERRED
    if (relation.element == CROSSMARK_UPDATE or
            relation.relationship_type in BLOCKING_RELATIONSHIP_TYPES):
        return BLOCKING
    return DEFERRED


def _remove_if_empty(element, child_tag):
    if element.find(child_tag) is None:
        element.getparent().remove(element)


def strip_relations(xml_doc, target_dois):
    """Remove do lote as relações cujo DOI alvo está em ``target_dois``.

    Containers ``rel:program`` e ``crossmark/updates`` que ficarem vazios
    também são removidos, pois o schema não os aceita sem filhos.
    """
    removed = []

    for node, relation in list(_relation_nodes(xml_doc)):
        if relation.target_doi not in target_dois:
            continue
        parent = node.getparent()
        parent.remove(node)
        removed.append(relation)
        if relation.element == RELATED_ITEM:
            _remove_if_empty(parent, _relations_tag('related_item'))
        else:
            _remove_if_empty(parent, _crossref_tag(xml_doc, 'update'))

    return removed


def set_batch_head(xml_doc, moment):
    """Renova o ``timestamp`` para um novo depósito do mesmo DOI.

    O ``doi_batch_id`` permanece o do XML. O Crossref ignora depósitos cujo
    ``timestamp`` não seja maior que o do depósito anterior.
    """
    timestamp = moment.strftime('%Y%m%d%H%M%S%f')[:17]
    xml_doc.find('.//' + _crossref_tag(xml_doc, 'timestamp')).text = timestamp
    return xml_doc
