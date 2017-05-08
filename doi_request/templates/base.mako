## coding: utf-8
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>SciELO | DOI Manager</title>
    <meta content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" name="viewport">
    
    
    <link rel="stylesheet" href="/static/bootstrap/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.5.0/css/font-awesome.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/ionicons/2.0.1/css/ionicons.min.css">
    <link rel="stylesheet" href="/static/adminlte/css/AdminLTE.min.css">
    <link rel="stylesheet" href="/static/adminlte/css/skins/_all-skins.min.css">
    <link rel="stylesheet" href="/static/plugins/daterangepicker/daterangepicker.css">

<link rel="stylesheet" href="/static/codemirror/css/codemirror.css">  
<%block name="stylesheet" />
  </head>
  <body class="hold-transition skin-blue layout-top-nav">
    <!-- Site wrapper -->
    <div class="wrapper">
      <header class="main-header">
        <nav class="navbar navbar-static-top">
            <div class="navbar-header">
              <a href="${request.route_url('list_deposits')}" class="navbar-brand"><b>SciELO</b> DOI Manager</a>
              <button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#navbar-collapse"><i class="fa fa-bars"></i></button>
            </div>
            <div class="collapse navbar-collapse pull-left" id="navbar-collapse">
              <ul class="nav navbar-nav">
                <li class="${'active' if navbar_active == 'deposits' else ''}">
                  <a href="${request.route_url('list_deposits')}">
                    <i class="fa fa-cloud"></i> <span> ${_(u'Depósitos')}</span>
                  </a>
                </li>
                <li class="${'active' if navbar_active == 'deposit_request' else ''}">
                  <a href="${request.route_url('deposit_request')}">
                    <i class="fa fa-cloud-upload"></i> <span> ${_(u'Depositar')}</span>
                  </a>
                </li>
                <li class="${'active' if navbar_active == 'expenses' else ''}">
                  <a href="${request.route_url('expenses')}">
                    <i class="fa fa-dollar"></i> <span> ${_(u'Custos')}</span>
                  </a>
                </li>
                <li class="${'active' if navbar_active == 'downloads' else ''}">
                  <a href="${request.route_url('downloads')}">
                    <i class="fa fa-cloud-download"></i> <span> ${_(u'Downloads')}</span>
                  </a>
                </li>
              </ul>
              <form action="${request.route_url('list_deposits')}" method="get" class="navbar-form navbar-left" role="search">
                <div class="input-group">
                  <input type="text" name="filter_pid_doi" id="navbar-search-input" class="form-control" placeholder="${_(u'pesquise por DOI ou PID')}">
                </div>
              </form>
            </div>
            <div class="navbar-custom-menu">
              <ul class="nav navbar-nav">
                <li class="dropdown messages-menu">
                  <a href="#" class="dropdown-toggle" data-toggle="dropdown">
                    <i class="fa fa-gears"></i>
                  </a>
                  <ul class="dropdown-menu">
                    <li class="header">Settings</li>
                    <li>
                      <ul class="menu">
                        <li class="content"><!-- start message -->
                          <dt>${_(u'Prefixo no Crossref')}</dt>
                          <dd>${crossref_prefix}</dd>
                          <dt>${_(u'Usuário no Crossref')}</dt>
                          <dd>${crossref_user_api}</dd>
                          <dt>${_(u'Nome do depositante')}</dt>
                          <dd>${crossref_depositor_name}</dd>
                          <dt>${_(u'E-mail do depositante')}</dt>
                          <dd>${crossref_depositor_email}</dd>
                        </li>
                      </ul>
                    </li>
                  </ul>
                </li>
              </ul>
            </div>
        </nav>
      </header>
      <!-- Content Wrapper. Contains page content -->
      <div class="content-wrapper">
          <!-- Main content -->
          <section class="content">
            <%block name="central_container" />
          </section>
          <!-- /.content -->
      </div>
      <!-- /.content-wrapper -->
      <footer class="main-footer">
          <div class="pull-right hidden-xs">
            <b>Version</b> ${version}
          </div>
        <strong>SciELO DOI Manager</strong>
      </footer>
    </div>
    <!-- ./wrapper -->
    <script src="/static/plugins/jQuery/jquery-2.2.3.min.js"></script>
    <script src="/static/bootstrap/js/bootstrap.min.js"></script>
    <script src="/static/plugins/slimScroll/jquery.slimscroll.min.js"></script>
    <script src="/static/plugins/fastclick/fastclick.js"></script>
    <script src="/static/adminlte/js/app.min.js"></script>
    <script src="/static/adminlte/js/demo.js"></script>
    <script src="/static/plugins/daterangepicker/moment.min.js"></script>
    <script src="/static/plugins/daterangepicker/daterangepicker.js"></script>
    <script src="/static/plugins/datepicker/bootstrap-datepicker.js"></script>
    <%block name="footer_js" />
  </body>
</html>
