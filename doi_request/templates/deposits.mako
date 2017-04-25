<%inherit file="base.mako"/>

<%block name="central_container">
  <div class="box box-primary collapsed-box">
    <div class="box-header with-border">
      <h3 class="box-title">${_('Filtros')}</h3>
      <div class="box-tools pull-right">
        <button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-plus"></i>
        </button>
      </div>
    </div>
    <div class="box-body">
      <form name="filter" action="${request.route_url('list_deposits')}" method="get">
        <div class="form-group">
          <label>${_(u'ISSN')}</label>
            <input name="filter_issn" type="text" class="form-control" value="${filter_issn or ''}"></input>
        </div>
        <div class="form-group">
          <label>${_(u'Prefix')}</label>
            <input name="filter_prefix" type="text" class="form-control" value="${filter_prefix or ''}"></input>
        </div>
        <div class="form-group">
          <label>${_(u'Situação de submissão')}</label>
          <select name="filter_submission_status" class="form-control">
            <option value="" ${'selected' if filter_submission_status == '' else ''}>${_(u'todos')}</option>
            % for item in status_to_template:
              <option value="${item}" ${'selected' if filter_submission_status == item else ''}>${item}</option>
            % endfor
          </select>
        </div>
        <div class="form-group">
          <label>${_(u'Situação de depósito')}</label>
          <select name="filter_feedback_status" class="form-control">
            <option value="" ${'selected' if filter_feedback_status == '' else ''}>${_(u'todos')}</option>
            % for item in status_to_template:
              <option value="${item}" ${'selected' if filter_feedback_status == item else ''}>${item}</option>
            % endfor
          </select>
        </div>
        <div class="form-group">
          <label>${_(u'Data de início de processo')}</label>
          <div class="input-group">
            <div class="input-group-addon">
              <i class="fa fa-calendar"></i>
            </div>
            <input class="form-control pull-right" name="filter_start_range" type="text">
          </div>
          <!-- /.input group -->
        </div>
        <div class="form-group pull-right">
          <button type="submit" class="btn btn-primary">${_(u'aplicar')}</button>
        </div>
      </form>
    </div>
  </div>
  <div class="box box-primary">
    <div class="box-header with-border">
      <h3 class="box-title">${_('Depósitos')}</h3>
      <div class="box-tools pull-right">
        <div class="has-feedback">
          <form name="query_by_id" action="${request.route_url('list_deposits')}" method="get">
            <div class="input-group">
              <input type="text" name="pid_doi" class="form-control" placeholder="${_(u'pesquise por DOI ou PID')}">
              <span class="input-group-btn">
                <button type="submit" id="search-btn" class="btn btn-default btn-flat"><i class="fa fa-search"></i>
                </button>
              </span>
            </div>
          </form>
        </div>
      </div>
    </div>
    <div class="box-body">
      <div class="row">
      <%include file="deposits_paging.mako"/>
      </div>
      <table id="example2" class="table table-bordered table-hover">
        <thead>
          <tr>
            <th class="visible-md visible-lg"></th>
            <th class="visible-md visible-lg">${_(u'início de processo')}</th>
            <th class="visible-md visible-lg">${_(u'periódico')}</th>
            <th>${_(u'depósito')}</th>
            <th class="visible-md visible-lg">${_(u'prefixo')}</th>
            <th>${_(u'situação de submissão')}</th>
            <th>${_(u'situação de depósito')}</th>
            <th class="visible-md visible-lg">${_(u'funções')}</th>
          </tr>
        </thead>
        <tbody>
          % for ndx, item in enumerate(deposits):
            <tr>
              <td class="visible-md visible-lg">${offset+ndx+1}</td>
              <td class="visible-md visible-lg">${item.started_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
              <td class="visible-md visible-lg">${item.journal} (${item.issue_label})</td>
              <td><a href="${request.route_url('deposit', deposit_item_code=item.code)}">${item.code}</a></td>
              <td class="visible-md visible-lg">${item.prefix}</td>
              <td>
                <span class="label label-${status_to_template[item.submission_status or 'unknow'][0]}">${item.submission_status}</span>
              </td>
              <td>
                <span class="label label-${status_to_template[item.feedback_status or 'unknow'][0]}">${item.feedback_status or ''}</span>
              </td>
              <td class="visible-md visible-lg">
              <a href="${request.route_url('deposit', deposit_item_code=item.code)}">
                <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-folder-open"></i> ${_(u'detalhes')}</button>
              </a>
              <a href="${request.route_url('post_deposit', deposit_item_code=item.code)}">
                <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-cloud-upload"></i> ${_(u'resubmeter')}</button>
              </a>
              </td>
            </tr>
            % endfor
        </tbody>
      </table>
      <div class="row">
      <%include file="deposits_paging.mako"/>
      </div>
    </div>
  </div>
</%block>

<%block name="footer_js">
<script type="text/javascript">
  $('input[name="filter_start_range"]').daterangepicker(
{
    locale: {
      format: 'MM/DD/YYYY'
    },
    startDate: '${filter_from_date}',
    endDate: '${filter_to_date}'
});
</script>
</%block>