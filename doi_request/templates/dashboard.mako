<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Dashboard')}</h3>

  % if error_message:
    <div class="alert alert-danger">${error_message}</div>
  % endif

  % if current_user.is_admin:
    <div class="row">
      <div class="col-md-4">
        <div class="box box-primary">
          <div class="box-header with-border">
            <h3 class="box-title">${_(u'Criar usuário')}</h3>
          </div>
          <form action="${request.route_url('dashboard')}" method="post">
            <div class="box-body">
              <div class="form-group">
                <label>${_(u'Usuário')}</label>
                <input type="text" name="username" class="form-control" value="${form_values.get('username', '')}">
              </div>
              <div class="form-group">
                <label>${_(u'Senha')}</label>
                <input type="password" name="password" class="form-control">
              </div>
              <div class="checkbox">
                <label><input type="checkbox" name="is_admin" ${'checked' if form_values.get('is_admin') else ''}> ${_(u'Administrador')}</label>
              </div>
              <div class="checkbox">
                <label><input type="checkbox" name="is_active" ${'checked' if form_values.get('is_active', True) else ''}> ${_(u'Ativo')}</label>
              </div>
            </div>
            <div class="box-footer">
              <button type="submit" class="btn btn-primary">${_(u'Criar')}</button>
            </div>
          </form>
        </div>
      </div>

      <div class="col-md-8">
        <div class="box box-primary">
          <div class="box-header with-border">
            <h3 class="box-title">${_(u'Usuários')}</h3>
          </div>
          <div class="box-body table-responsive no-padding">
            <table class="table table-hover">
              <thead>
                <tr>
                  <th>${_(u'Usuário')}</th>
                  <th>${_(u'Administrador')}</th>
                  <th>${_(u'Ativo')}</th>
                  <th>${_(u'Criado em')}</th>
                </tr>
              </thead>
              <tbody>
                % for user in users:
                  <tr>
                    <td>${user.username}</td>
                    <td>${user.is_admin}</td>
                    <td>${user.is_active}</td>
                    <td>${user.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
                  </tr>
                % endfor
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  % else:
    <div class="box box-primary">
      <div class="box-header with-border">
        <h3 class="box-title">${_(u'Conta')}</h3>
      </div>
      <div class="box-body">
        <p><strong>${_(u'Usuário')}:</strong> ${current_user.username}</p>
        <p><strong>${_(u'Administrador')}:</strong> ${current_user.is_admin}</p>
        <p><strong>${_(u'Ativo')}:</strong> ${current_user.is_active}</p>
        <p><a href="${request.route_url('profile')}" class="btn btn-primary btn-sm">${_(u'Editar perfil')}</a></p>
      </div>
    </div>
  % endif

  <div class="box box-primary">
    <div class="box-header with-border">
      <h3 class="box-title">${_(u'Auditoria')}</h3>
    </div>
    <div class="box-body table-responsive no-padding">
      <table class="table table-hover">
        <thead>
          <tr>
            <th>${_(u'Data')}</th>
            <th>${_(u'Usuário')}</th>
            <th>${_(u'Ação')}</th>
            <th>${_(u'Alvo')}</th>
            <th>${_(u'Detalhes')}</th>
          </tr>
        </thead>
        <tbody>
          % for item in audit_logs:
            <tr>
              <td>${item.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
              <td>${item.actor_username or ''}</td>
              <td>${item.action}</td>
              <td>${item.target_type or ''} ${item.target_label or ''}</td>
              <td><small>${item.details or ''}</small></td>
            </tr>
          % endfor
        </tbody>
      </table>
    </div>
  </div>
</%block>
