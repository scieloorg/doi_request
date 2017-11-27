<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Custo mensal')}</h3>
  <table id="expenses" class="table table-bordered table-hover">
    <thead>
      <tr>
        <th>${_(u'Período')}</th>
        <th>${_(u'Retrospectivos')}</th>
        <th>${_(u'Novos')}</th>
        <th>${_(u'Total')}</th>
      </tr>
    </thead>
    <tbody>
      % for key, item in sorted(expenses.items(), reverse=True):
        <tr>
          <td>${key}</td>
          <td>$ ${format(item['retro'], '.2f')}</td>
          <td>$ ${format(item['new'], '.2f')}</td>
          <td>$ ${format(item['total'], '.2f')}</td>
          <td>
            <a href="${request.route_url('expenses_details')}?expenses_period=${key}">
              <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-cloud-upload"></i> ${_(u'detalhes')}</button>
            </a>
          </td>
        </tr>
        % endfor
    </tbody>
  </table>
</%block>
