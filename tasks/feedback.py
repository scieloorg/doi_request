def batch_feedback(xml_doc):
    """Resume o resultado de todos os registros do lote (um por DOI).

    O lote só é considerado ``success`` quando todos os registros são.
    Sem ``record_diagnostic``, devolve ``unknow`` e corpo vazio.
    """
    diagnostics = xml_doc.findall('.//record_diagnostic')
    if not diagnostics:
        return 'unknow', ''

    statuses = [diagnostic.get('status').lower() for diagnostic in diagnostics]
    failures = [status for status in statuses if status != 'success']
    body = '\n'.join(
        '%s: %s' % (diagnostic.findtext('doi'), diagnostic.findtext('msg'))
        for diagnostic in diagnostics)

    return (failures[0] if failures else 'success'), body
