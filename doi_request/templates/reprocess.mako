<%inherit file="base.mako"/>
<%block name="central_container">
  <div class="row">
    <div class="col-md-8">
      <div class="box box-primary">
        <div class="box-header with-border">
          <h3 class="box-title">Reprocessar DOIs / Prefixes</h3>
        </div>
        <form action="${request.route_url('reprocess_submit')}" method="post">
          <div class="box-body">
            <p>Informe uma lista de DOIs ou prefixes (um por linha ou separados por vírgula). Apenas DOIs válidas na Crossref serão levadas em conta para evitar cobranças indevidas.</p>
            <div class="form-group">
              <textarea name="dois_or_prefixes" class="form-control" rows="8" placeholder="10.1234/abcd\n10.5678\n10.9999/test"></textarea>
            </div>
            <div class="checkbox">
              <label>
                <input type="checkbox" checked name="dry_run" value="on"> Dry-run / Preview (sem executar atualizações)
              </label>
            </div>
            <div class="form-group">
              <label>Rate limit (segundos entre validações na Crossref)</label>
              <input type="number" name="rate_limit_seconds" value="1.0" min="0" step="0.1" class="form-control" />
            </div>
          </div>
          <div class="box-footer">
            <button type="submit" class="btn btn-primary">Executar</button>
          </div>
        </form>
      </div>

      % if preview_results:
      <div class="box box-info">
        <div class="box-header with-border">
          <h3 class="box-title">Preview</h3>
        </div>
        <div class="box-body">
          <ul>
            % for item in preview_results:
            <li>
              ${item['input']} - ${item['reason']} - ${'OK' if item['valid'] else 'SKIPPED'}
            </li>
            % endfor
          </ul>
        </div>
      </div>
      % endif

      % if error:
      <div class="alert alert-warning">
        ${error}
      </div>
      % endif
    </div>

    <div class="col-md-4">
      <div class="box box-default">
        <div class="box-header with-border">
          <h3 class="box-title">Histórico de execuções</h3>
        </div>
        <div class="box-body">
          % if jobs:
            <ul class="list-unstyled">
              % for job in jobs:
              <li>
                <strong>#${job.id}</strong>
                - ${job.created_at.strftime('%Y-%m-%d %H:%M')}<br>
                <small>${job.status} / total ${job.total} / processados ${job.processed} / ignorados ${job.skipped}</small>
              </li>
              % endfor
            </ul>
          % else:
            <p>Nenhuma execução registrada.</p>
          % endif
        </div>
      </div>
    </div>
  </div>
</%block>
