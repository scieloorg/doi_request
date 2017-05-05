<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Detalhes de custos')} (${period.strftime('%B %Y')})</h3>
  <div class="row">
    <%include file="paging.mako"/>
  </div>
  <table id="expenses" class="table table-bordered table-hover">
    <thead>
      <tr>
        <th class="visible-md visible-lg"></th>
        <th>${_(u'data de registro')}</th>
        <th>${_(u'doi')}</th>
        <th class="visible-md visible-lg">${_(u'ano de publicação')}</th>
        <th class="visible-md visible-lg">${_(u'retrospectivo')}</th>
        <th>${_(u'valor')}</th>
      </tr>
    </thead>
    <tbody>
      % for ndx, item in enumerate(expenses):
        <tr>
          <td class="visible-md visible-lg">${offset+ndx+1}</td>
          <td>${item.registry_date.strftime('%Y-%m-%d %H:%M:%S')}</td>
          <td><a href="https://doi.org/${item.doi}" target="_blank">${item.doi}</a></td>
          <td class="visible-md visible-lg">${item.publication_year}</td>
          <td class="visible-md visible-lg">${item.retro}</td>
          <td>$ ${format(item.cost, '.2f')}</td>
        </tr>
        % endfor
    </tbody>
  </table>
  <div class="row">
    <%include file="paging.mako"/>
  </div>
</%block>
