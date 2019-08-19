DOI Manager
===========

Gerencia e realiza depósitos dos metadados dos artigos junto ao Crossref.

Esta aplicação obtém os dados do Article Meta, via Thrift.


Instalação
----------

Para instalar no modo deselvolvimento, execute o comando::

    pip install -e .[dev]


Serviços para Produção
----------------------

Para o funcionamento da aplicação, é necessário configurar:

- Banco de Dados: responsável por armazenar os registros dos documentos
- exportdoi: responsável por consultar os documentos processados no Article Meta, de acordo com os parâmetros informados, e armazená-los na Base de Dados.
  É executado através da linha de comando::

        processing_export_doi [-h] [--issns_file ISSNS_FILE] --collection
                                 COLLECTION [--from_date FROM_DATE]
                                 [--until_date UNTIL_DATE]
                                 [--date_range DATE_RANGE]
                                 [--logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                                 [--sentry_handler SENTRY_HANDLER]
                                 [issns [issns ...]]

        Argumentos:
            issns                 ISSN's seperados por espaço

        Argumentos opcionais:
            -h, --help            Exibe este texto de ajuda
            --issns_file ISSNS_FILE, -i ISSNS_FILE
                                  Path completo para um arquivo TXT com a lista de ISSNs
                                  a serem exportados
            --collection COLLECTION, -c COLLECTION
                                  Acrônimo da coleção a ser exportada
            --from_date FROM_DATE, -f FROM_DATE
                                  Data inicial de processamento dos documentos
                                  (processing_date), no formato ISO no formato YYYY-MM-DD,
                                  para a exportação.
                                  Ex.: 2019-07-20
            --until_date UNTIL_DATE, -g UNTIL_DATE
                                  Data final de processamento dos documentos
                                  (processing_date), no formato ISO no formato YYYY-MM-DD,
                                  para a exportação.
                                  Ex.: 2019-07-20
            --date_range DATE_RANGE, -r DATE_RANGE
                                  Número de dias anteriores à data corrente para a data de
                                  processamento dos documentos a serem exportados. Este
                                  sobrescreverá qualquer definição dos argumentos from_date
                                  e until_date.
            --logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}, -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                                  Logging level
            --sentry_handler SENTRY_HANDLER
                                  DSN do Sentry. Esta opção tem precedência sobre a
                                  configuração da variável de ambiente SENTRY_HANDLER


- Dashboard: interface WEB desta aplicação
- Celeryworker: responsável por enfileirar as tarefas de depósito no CrossRef
- Celeryworker-dispacher: responsável por executar as tarefas enfileiradas pelo Celeryworker. Este não recebe o status do depósito de documentos.
- Celeryworker-releaser: responsável por consultar o status do depósito de documentos no CrossRef.
- Redis: armazena as filas
