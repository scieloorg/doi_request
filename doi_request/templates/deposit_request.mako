<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>
    ${_(u'Requisitar depósitos')}
  </h3>
  <p>
      ${_(u"Indicar os PID's que serão resubmetidos.")}
  </p>
  <ul>
    <li>${_("Cada PID deve estar em um linha")}</li>
  </ul>
  <form action="${request.route_url('deposit_post')}" method="post" role="form">
    <div class="form-group">
      <label>${_('lista de PIDs')}</label>
      <textarea name="pids" rows="10" class="form-control" placeholder="${_(u'lista de pids ex: S0102-69092006000200003')}"></textarea>
    </div>
    <button type="submit" class="btn btn-primary btn-sm"><i class="fa fa-cloud-upload"></i> ${_(u'submeter')}</button>
  </form>
</%block>