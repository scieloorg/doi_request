<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>SciELO | DOI Manager Login</title>
    <meta content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" name="viewport">
    <link rel="stylesheet" href="/static/bootstrap/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.5.0/css/font-awesome.min.css">
    <link rel="stylesheet" href="/static/adminlte/css/AdminLTE.min.css">
  </head>
  <body class="hold-transition login-page">
    <div class="login-box">
      <div class="login-logo">
        <a href="${request.route_url('login')}"><b>SciELO</b> DOI Manager</a>
      </div>
      <div class="login-box-body">
        <p class="login-box-msg">${_(u'Entre para acessar o sistema')}</p>
        % if error_message:
          <div class="alert alert-danger">${error_message}</div>
        % endif
        <form action="${request.route_url('login')}" method="post">
          <input type="hidden" name="next" value="${next_url}">
          <div class="form-group has-feedback">
            <input type="text" name="username" class="form-control" value="${username or ''}" placeholder="${_(u'usuário')}" required>
            <span class="glyphicon glyphicon-user form-control-feedback"></span>
          </div>
          <div class="form-group has-feedback">
            <input type="password" name="password" class="form-control" placeholder="${_(u'senha')}" required>
            <span class="glyphicon glyphicon-lock form-control-feedback"></span>
          </div>
          <div class="row">
            <div class="col-xs-12">
              <button type="submit" class="btn btn-primary btn-block btn-flat">${_(u'entrar')}</button>
            </div>
          </div>
        </form>
      </div>
      <p class="text-center" style="margin-top: 12px;"><small>Version ${version}</small></p>
    </div>
  </body>
</html>
