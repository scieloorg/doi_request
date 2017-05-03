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
          <p><a href="https://doi.org/${deposit.doi}" target="_blank">https://doi.org/${deposit.doi or ''}</a></p>
          <strong>DOI BATCH ID</strong>
          <p>${deposit.doi_batch_id}</p>
          <strong>${_(u'Periódico')}</strong>
          <p>${deposit.journal}</p>
          <strong>${_(u'Iniciado em')}</strong>
          <p>${deposit.started_at}</p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de submissão')}</strong>
          <p><span class="label label-${submission_status_to_template[deposit.submission_status or 'unknow'][0]}">${deposit.submission_status or 'unknow'}</span></p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.submission_updated_at}</p>
        </div>
        <div class="col-md-4 col-sm-8 col-xs-16">
          <strong>${_(u'Situação de depósito')}</strong>
          <p><span class="label label-${feedback_status_to_template[deposit.feedback_status or 'unknow'][0]}">${deposit.feedback_status or 'unknow'}</span></p>
          <strong>${_(u'Atualizado em')}</strong>
          <p>${deposit.feedback_updated_at}</p>
        </div>
      </div>
      <div class="row">
        <div class="col-md-12 col-sm-24 col-xs-48">
          <a href="${request.route_url('deposit_post')}?pids=${deposit.pid}">
            <button type="button" class="btn btn-primary btn-sm pull-right"><i class="fa fa-cloud-upload"></i> ${_(u'resubmeter')}</button>
          </a>
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
        % for event in deposit.timeline:
          <li>
            <i class="fa ${feedback_status_to_template[event.status or 'unknow'][2]} bg-${timeline_status_to_template[event.status or 'unknow'][1]}"></i>
            <div class="timeline-item">
              <span class="time">
                <i class="fa fa-clock-o"></i>
                ${event.date}
              </span>
              <h3 class="timeline-header">
                (${event.type}) ${event.title}
              </h3>
              % if event.body:
                <div class="timeline-body">
                  ${event.body}
                </div>
              % endif
            </div>
          </li>
        % endfor
      </ul>
    </div>
    <div class="tab-pane" id="submission_details">
      <strong>${_(u'XML é válido')}</strong>
      <p>${deposit.is_xml_valid}</p>
      <strong>${_(u'XML com referências é válido')}</strong>
      <p>${deposit.has_submission_xml_valid_references}</p>
      <strong>${_(u'Situação da submissão')}</strong>
      <p>${deposit.submission_status}</p>
      <strong>${_(u'XML de depósito')}</strong>
      <p><textarea class="form-control" id="submission_xml">${deposit.submission_xml}</textarea></p>
    </div>
    <div id="deposit_details" class="tab-pane">
      <strong>${_(u'Situação do depósito')}</strong>
      <p>${deposit.feedback_status}</p>
      <strong>${_(u'XML de resultado do depósito')}</strong>
      <p><textarea class="form-control" id="feedback_xml">${deposit.feedback_xml}</textarea></p>
    </div>
  </div>
</div>
</%block>

<%block name="footer_js">
  <script src="/static/codemirror/js/codemirror.js"></script>
  <script src="/static/codemirror/mode/xml/xml.js"></script>
  <script source="javascript">
    var myCodeMirror_submission = CodeMirror.fromTextArea(document.getElementById("submission_xml"), {
      mode: 'application/xml',
      lineNumbers: true,
      lineWrapping: true,
      readOnly: true,
    });
    var myCodeMirror_feedback = CodeMirror.fromTextArea(document.getElementById("feedback_xml"), {
      mode: 'application/xml',
      lineNumbers: true,
      lineWrapping: true,
      readOnly: true
    });
    $(function() {
      $('a[data-toggle="tab"]').on('shown.bs.tab', function(){
        myCodeMirror_submission.refresh();
        myCodeMirror_feedback.refresh();
      });
    });
  </script>
</%block>
