<%inherit file="base.mako"/>

<%block name="central_container">
  <h1>${_(u'Depositos')}</h1>
  <table id="example2" class="table table-bordered table-hover">
    <thead>
      <tr>
        <th>${_(u'coleção')}</th>
        <th>${_(u'DOI')}</th>
        <th>${_(u'documento')}</th>
        <th>${_(u'Situação de Submissão')}</th>
        <th>${_(u'Situação de depósito')}</th>
      </tr>
    </thead>
    <tbody>
      % for item in deposits:
        <tr>
          <td>${item.collection_acronym}</td>
          <td>${item.doi}</td>
          <td><a href="${request.route_url('deposit', deposit_item_code=item.code)}">${item.code}</a></td>
          <td>${item.submission_status or ''}</td>
          <td>${item.feedback_status or ''}</td>
        </tr>
        % endfor
    </tbody>
    <tfoot>
      <tr>
        <th>${_(u'coleção')}</th>
        <th>${_(u'DOI')}</th>
        <th>${_(u'documento')}</th>
        <th>${_(u'Situação de Submissão')}</th>
        <th>${_(u'Situação de depósito')}</th>
      </tr>
    </tfoot>
  </table>
</%block>