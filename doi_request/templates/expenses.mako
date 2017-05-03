<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Custo mensal')}</h3>
  <table id="expenses" class="table table-bordered table-hover">
    <thead>
      <tr>
        <th>${_(u'Período')}</th>
        <th>${_(u'Custos')}</th>
      </tr>
    </thead>
    <tbody>
      % for ndx, item in enumerate(expenses):
        <tr>
          <td>${item[0].strftime('%B %Y')}</td>
          <td>$ ${format(item[1], '.2f')}</td>
          <td>
            <a href="${request.route_url('expenses_details')}?period=${item[0]}">
              <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-cloud-upload"></i> ${_(u'detalhes')}</button>
            </a>
          </td>
        </tr>
        % endfor
    </tbody>
  </table>
</%block>
