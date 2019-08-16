DOI Manager
===========

Gerencia e realiza depósitos dos metadados dos artigos junto ao Crossref.


Instalação
----------

Para instalar no modo deselvolvimento, execute o comando::

    pip install -e .[dev]


Serviços para Produção
----------------------

Para o funcionamento da aplicação, é necessário configurar:

- Banco de Dados: responsável por armazenar os registros dos documentos
- exportdoi: responsável por consultar os documentos processados nos últimos 15 dias (processing_date) no Article Meta e armazená-los na Base de Dados. É executado através da linha de comando::

    processing_export_doi

- Dashboard: interface WEB desta aplicação
- Celeryworker: responsável por enfileirar as tarefas de depósito no CrossRef
- Celeryworker-dispacher: responsável por executar as tarefas enfileiradas pelo Celeryworker. Este não recebe o status do depósito de documentos.
- Celeryworker-releaser: responsável por consultar o status do depósito de documentos no CrossRef.
- Redis: armazena as filas
