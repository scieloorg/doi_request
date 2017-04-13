<%inherit file="base.mako"/>

<%block name="central_container">
<div class="nav-tabs-custom">
  <ul class="nav nav-tabs">
    <li class="active"><a href="#deposit" data-toggle="tab" aria-expanded="true">${_(u'Depósito')}</a></li>
    <li class=""><a href="#timeline" data-toggle="tab" aria-expanded="false">${_(u'Linha do tempo')}</a></li>
    <li class=""><a href="#submission_details" data-toggle="tab" aria-expanded="false">${_(u'Detalhes da submissão')}</a></li>
    <li class=""><a href="#deposit_details" data-toggle="tab" aria-expanded="false">${_(u'Detalhes do depósito')}</a></li>
  </ul>
  <div class="tab-content">
    <div id="deposit" class="tab-pane active">
      <div class="row">
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>DOI</strong>
          <p><a href="https://doi.org/${deposit.doi}" target="_blank">https://doi.org/${deposit.doi}</a></p>
          <strong>DOI BATCH ID</strong>
          <p>${deposit.doi_batch_id}</p>
          <strong>${_(u'Iniciado em')}</strong>
          <p>${deposit.started_at}</p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de submissão')}</strong>
          <p><span class="label label-${submission_status_to_template[deposit.submission_status or 'unknow']}">${deposit.submission_status or 'unknow'}</span></p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.submission_updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de depósito')}</strong>
          <p><span class="label label-${submission_status_to_template[deposit.feedback_status or 'unknow']}">${deposit.feedback_status or 'unknow'}</span></p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.feedback_updated_at}</p>
        </div>
      </div>
    </div>
    <div class="tab-pane" id="timeline">
      <ul class="timeline">
          <li class="time-label">
            <span class="bg-gray">
              ${deposit.started_at}
            </span>
          </li>
          <li>
            <i class="fa fa-info bg-default"></i>
            <div class="timeline-item">
              <span class="time">
                <i class="fa fa-clock-o"></i>
                ${deposit.started_at}
              </span>
              <h3 class="timeline-header">
                ${_('Iniciado processo de requisição de DOI')}
              </h3>
            </div>
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
          <li>
            <i class="fa fa-info bg-default"></i>
            <div class="timeline-item">
              <span class="time">
                <i class="fa fa-clock-o"></i>
                ${deposit.updated_at}
              </span>
              <h3 class="timeline-header">
                ${_('Data da última atualização')}
              </h3>
            </div>
          </li>
      </ul>
    </div>
    <div class="tab-pane" id="submission_details">
      <strong>${_(u'Log da submissão')}</strong>
      <p>${deposit.submission_log}</p>
      <strong>${_(u'XML é válido')}</strong>
      <p>${deposit.xml_is_valid}</p>
      <strong>${_(u'Situação da submissão')}</strong>
      <p>${deposit.submission_status}</p>
      <strong>${_(u'Código HTTP de situação da submissão')}</strong>
      <p>${deposit.submission_status_code}</p>
      <strong>${_(u'Resposta da submissão')}</strong>
      <p>${deposit.submission_response}</p>
      <strong>${_(u'XML de depósito')}</strong>
      <p>${deposit.deposit_xml}</p>
    </div>
    <div id="deposit_details" class="tab-pane">
      <strong>${_(u'Log do depósito')}</strong>
      <p>${deposit.submission_log}</p>
      <strong>${_(u'Situação do depósito')}</strong>
      <p>${deposit.feedback_status}</p>
      <strong>${_(u'Código HTTP de verificação da situação do depósito')}</strong>
      <p>${deposit.feedback_request_status_code}</p>
      <strong>${_(u'XML de resultado do depósito')}</strong>
      <p>${deposit.feedback_xml}</p>
    </div>
  </div>
</div>
</%block>