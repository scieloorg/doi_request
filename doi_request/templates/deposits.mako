<%inherit file="base.mako"/>

<%block name="central_container">
  <div class="box box-primary">
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
            <input name="issn" type="text" class="form-control" value="${filter_issn or ''}"></input>
        </div>
        <div class="form-group">
          <label>${_(u'Prefix')}</label>
            <input name="prefix" type="text" class="form-control" value="${filter_prefix or ''}"></input>
        </div>
        <div class="form-group">
          <label>${_(u'Situação de submissão')}</label>
          <select name="submission_status" class="form-control">
            <option value="" ${'selected' if filter_submission_status == '' else ''}>${_(u'todos')}</option>
            % for item in status_to_template:
              <option value="${item}" ${'selected' if filter_submission_status == item else ''}>${item}</option>
            % endfor
          </select>
        </div>
        <div class="form-group">
          <label>${_(u'Situação de depósito')}</label>
          <select name="feedback_status" class="form-control">
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
        <div class="col-sm-4">
          ${_(u'mostrando')} ${offset+1} ${_(u'a')} ${offset + limit} ${_(u'de')} ${ total } ${_(u'itens')}
        </div>
        <div class="col-sm-8">
          <ul class="pagination pull-right">
            % if offset > 0:
              <li class="paginate_button previous">
                <a href="/?offset=${offset-limit}">Previous</a>
              </li>
            % else:
              <li class="paginate_button previous disabled">
                <a href="#">Previous</a>
              </li>
            % endif
            % for offset_item in range(offset, total, limit)[0:4]:
            <li class="paginate_button previous">
              <a href="/?offset=${offset_item}">${int((offset_item/limit)+1)}</a>
            </li>
            % endfor
            % if offset+limit <= total:
              <li class="paginate_button next" id="example2_next">
                <a href="/?offset=${offset+limit}">Next</a>
              </li>
            % else:
              <li class="paginate_button next disabled">
                <a href="#">Next</a>
              </li>
            % endif
          </ul>
        </div>
      </div>
      <table id="example2" class="table table-bordered table-hover">
        <thead>
          <tr>
            <th></th>
            <th>${_(u'início de processo')}</th>
            <th>${_(u'periódico')}</th>
            <th>${_(u'depósito')}</th>
            <th>${_(u'prefixo')}</th>
            <th>${_(u'situação de submissão')}</th>
            <th>${_(u'situação de depósito')}</th>
            <th>${_(u'funções')}</th>
          </tr>
        </thead>
        <tbody>
          % for ndx, item in enumerate(deposits):
            <tr>
              <td>${offset+ndx+1}</td>
              <td>${item.started_at}</td>
              <td>${item.journal} (${item.issue_label})</td>
              <td><a href="${request.route_url('deposit', deposit_item_code=item.code)}">${item.code}</a></td>
              <td>${item.prefix}</td>
              <td>
                <span class="label label-${status_to_template[item.submission_status or 'unknow'][0]}">${item.submission_status}</span>
              </td>
              <td>
                <span class="label label-${status_to_template[item.feedback_status or 'unknow'][0]}">${item.feedback_status or ''}</span>
              </td>
              <td>
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
        <div class="col-sm-4">
          ${_(u'mostrando')} ${offset+1} ${_(u'a')} ${offset + limit} ${_(u'de')} ${ total } ${_(u'itens')}
        </div>
        <div class="col-sm-8">
          <ul class="pagination pull-right">
            % if offset > 0:
              <li class="paginate_button previous">
                <a href="/?offset=${offset-limit}">Previous</a>
              </li>
            % else:
              <li class="paginate_button previous disabled">
                <a href="#">Previous</a>
              </li>
            % endif
            % for offset_item in range(offset, total, limit)[0:4]:
            <li class="paginate_button previous">
              <a href="/?offset=${offset_item}">${int((offset_item/limit)+1)}</a>
            </li>
            % endfor
            % if offset+limit <= total:
              <li class="paginate_button next" id="example2_next">
                <a href="/?offset=${offset+limit}">Next</a>
              </li>
            % else:
              <li class="paginate_button next disabled">
                <a href="#">Next</a>
              </li>
            % endif
          </ul>
        </div>
      </div>
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