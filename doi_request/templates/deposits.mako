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
          <label>${_(u'Situação do depósito')}</label>
          <select name="feedback_status" class="form-control">
            <option value=""></option>
            % for item in feedback_status_to_template:
              <option value="${item}">${item}</option>
            % endfor
          </select>
        </div>
        <div class="form-group">
          <label>${_(u'Data de início de processo')}</label>
          <div class="input-group">
            <div class="input-group-addon">
              <i class="fa fa-calendar"></i>
            </div>
            <input class="form-control pull-right" name="feedback_start_range" type="text">
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
              <input type="text" name="query" class="form-control" placeholder="${_(u'pesquise por DOI ou PID')}">
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
      <table id="example2" class="table table-bordered table-hover">
        <thead>
          <tr>
            <th>${_(u'depósito')}</th>
            <th>${_(u'situação de submissão')}</th>
            <th>${_(u'situação de depósito')}</th>
            <th>${_(u'funções')}</th>
          </tr>
        </thead>
        <tbody>
          % for item in deposits:
            <tr>
              <td><a href="${request.route_url('deposit', deposit_item_code=item.code)}">${item.code}</a></td>
              <td>
                <span class="label label-${submission_status_to_template[item.submission_status or 'unknow']}">${item.submission_status or 'unknow'}</span>
              </td>
              <td>
                <span class="label label-${feedback_status_to_template[item.feedback_status or 'unknow']}">${item.feedback_status or 'unknow'}</span>
              </td>
              <td>
              <a href="${request.route_url('deposit', deposit_item_code=item.code)}">
                <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-folder-open"></i> ${_(u'detalhes')}</button>
              </a>
              <a href="#">
                <button type="button" class="btn btn-primary btn-sm"><i class="fa fa-cloud-upload"></i> ${_(u'enviar')}</button>
              </a>
              </td>
            </tr>
            % endfor
        </tbody>
      </table>
    </div>
  </div>
</%block>

<%block name="footer_js">
<script type="text/javascript">
  $('input[name="feedback_start_range"]').daterangepicker(
{
    locale: {
      format: 'MM/DD/YYYY'
    },
    startDate: '${filter_from_date}',
    endDate: '${filter_to_date}'
});
</script>
</%block>