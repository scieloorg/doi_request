<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Custos')}</h3>
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
          <td>${item[0].strftime('%Y-%m')}</td>
          <td>$ ${format(item[1], '.2f')}</td>
        </tr>
        % endfor
    </tbody>
  </table>
</%block>
