<%inherit file="base.mako"/>

<%block name="central_container">
  <div class="box box-primary">
    <div class="box-header with-border">
      <h3 class="box-title">${_(u'Deposito')}</h3>
    </div>
    <div class="box-body">
      <div class="row">
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>DOI</strong>
          <p>${deposit.doi}</p>
          <strong>DOI BATCH ID</strong>
          <p>${deposit.doi_batch_id}</p>
          <strong>${_(u'Iniciado em')}</strong>
          <p>${deposit.started_at}</p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de submissão')}</strong>
          <p>${deposit.submission_status}</p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.submission_updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de depósito')}</strong>
          <p>${deposit.feedback_status}</p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.feedback_updated_at}</p>
        </div>
      </div>
    </div>
  </div>
  <div class="box box-primary collapsed-box">
    <div class="box-header with-border">
      <h3 class="box-title">${_(u'Linha do tempo')}</h3>
      <div class="box-tools pull-right">
        <button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-plus"></i></button>
      </div>
    </div>
    <div class="box-body">
      <ul class="timeline">
          <li class="time-label">
            <span class="bg-gray">
              ${deposit.started_at}
            </span>
          </li>
        % for event_date, event_status, event_icon, event_signal, event_message in timeline:
          <li>
            <i class="fa ${event_icon} bg-${event_signal}"></i>
            <div class="timeline-item">
              <span class="time">
                <i class="fa fa-clock-o"></i>
                ${event_date}
              </span>
              <h3 class="timeline-header">
                ${event_message}
              </h3>
            </div>
          </li>
        % endfor
      </ul>
    </div>
  </div>
</%block>