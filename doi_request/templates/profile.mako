<%inherit file="base.mako"/>

<%block name="central_container">
  <h3>${_(u'Meu perfil')}</h3>

  % if error_message:
    <div class="alert alert-danger">${error_message}</div>
  % endif

  <div class="row">
    <div class="col-md-4">
      <div class="box box-primary">
        <div class="box-header with-border">
          <h3 class="box-title">${_(u'Conta')}</h3>
        </div>
        <div class="box-body">
          <p><strong>${_(u'Usuário')}:</strong> ${current_user.username}</p>
          <p><strong>${_(u'Administrador')}:</strong> ${current_user.is_admin}</p>
          <p><strong>${_(u'Ativo')}:</strong> ${current_user.is_active}</p>
        </div>
      </div>
    </div>
    <div class="col-md-8">
      <div class="box box-primary">
        <div class="box-header with-border">
          <h3 class="box-title">${_(u'Alterar senha')}</h3>
        </div>
        <form action="${request.route_url('profile')}" method="post">
          <div class="box-body">
            <div class="form-group">
              <label>${_(u'Senha atual')}</label>
              <input type="password" name="current_password" class="form-control">
            </div>
            <div class="form-group">
              <label>${_(u'Nova senha')}</label>
              <input type="password" name="new_password" class="form-control">
            </div>
            <div class="form-group">
              <label>${_(u'Confirmar nova senha')}</label>
              <input type="password" name="confirm_password" class="form-control">
            </div>
          </div>
          <div class="box-footer">
            <button type="submit" class="btn btn-primary">${_(u'Atualizar senha')}</button>
          </div>
        </form>
      </div>
    </div>
  </div>

  <div class="box box-primary">
    <div class="box-header with-border">
      <h3 class="box-title">${_(u'Minhas ações recentes')}</h3>
    </div>
    <div class="box-body table-responsive no-padding">
      <table class="table table-hover">
        <thead>
          <tr>
            <th>${_(u'Data')}</th>
            <th>${_(u'Ação')}</th>
            <th>${_(u'Alvo')}</th>
            <th>${_(u'Detalhes')}</th>
          </tr>
        </thead>
        <tbody>
          % for item in audit_logs:
            <tr>
              <td>${item.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td>
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
