# DOI Manager

É uma ferramenta desenvolvida para automatizar os registros de DOI pelas coleções que adotam a métodologia SciELO. Por meio do DOI Manager é possível gerenciar novos depósitos, re-depositar, contabilizar custos e buscar informações sobre sucesso e falha de depósitos passados.

## Documentação

Para mais informações sobre a ferramenta acesse o [índice da documentação](docs/README.md).

## Métodos de instalação

Os tópicos a seguir cobrem os requisitos básicos para a instalação da aplicação.

### Variáveis de ambiente

Configurar as variáveis de ambiente é um pré requisito para utilizar o DOI Manager. Os dados de configuração podem variar de acordo com o tipo de instalação, ambiente utilizado, sistema operacional, etc. Consulte a pessoa responsável pelo ambiente de `deploy` para obter mais detalhes.

As seguintes variáveis devem ser configuradas:

- `ARTICLEMETA_ADMINTOKEN` - Token utilizado para conectar ao ArticleMeta;
- `ARTICLEMETA_THRIFTSERVER` - Endereço do servidor thrift do ArticleMeta;
- `COLLECTION_ACRONYM` - Acrônimo da coleção em que o DOI Manager irá rodar;
- `CROSSREF_API_PASSWORD` - Senha da API do [Crossref](https://github.com/CrossRef/rest-api-doc)
- `CROSSREF_API_USER` - Usuário da API do Crossref;
- `CROSSREF_DEPOSITOR_EMAIL` - E-mail utilizado pelo depositor do DOI no Crossref;
- `CROSSREF_DEPOSITOR_NAME` - Nome utilizado pelo depositor do DOI no Crossref;
- `CROSSREF_PREFIX` - Prefixo utilizado pelo depositor do DOI no Crossref (ex: a SciELO utiliza o `10.1590`);
- `SQL_ENGINE` - URI utilizada para conectar ao Banco de dados (PostgreSQL) (ex: `postgresql+psycopg://usuario:senha@db:5432/banco_de_dados`);
- `LOGGING_LEVEL` - Nível de log utilizado pela aplicação;
- `SESSION_SECRET` - Segredo usado para assinar a sessão autenticada da interface web;

### Instalação direta

Para realizar uma instalação direta, sem auxílio de containers, deve-se atentar para os seguintes pré requisitos:

- Python **3.14.3**
- Libxml2 dev
- PostgreSQL [**9.5**](https://hub.docker.com/r/scieloorg/inbox_postgres)
- Celery **4.2.1**
- Redis >= **4.0** <= **5.0**
- Musl dev

Faça o download da aplicação, desempacote o código e execute o comando:

```shell
pip install -r requirements.txt
```

Faça uma cópia dos arquivos de inicialização e configure as variáveis necessárias ao seu ambiente:

```shell
cp production.ini-TEMPLATE config.ini
cp alembic.ini-TEMPLATE alembic.ini
```

### Instalação via imagem Docker

É possível usar o `docker-compose` para facilitar a instalação do ambiente via Docker, utilize o comando:

```shell
docker compose up
```

O build das imagens será realizado e o ambiente deve ser inicialiado de acordo com o processo definido no arquivo `docker-compose.yml`.

## Autenticação

O acesso à interface web pode ser protegido por login local da aplicação.

### Rollout em produção

1. Fazer deploy do código novo.
2. Executar a migration:

```shell
alembic upgrade head
```

3. Criar ou atualizar o usuário administrador:

```shell
doi_request_create_admin --username admin --password 'senha-forte'
```

4. Reiniciar o serviço web.

Em ambientes Docker, os comandos podem ser executados com `docker compose run --rm ...` usando a imagem da aplicação.


## Métodos de operação

O DOI Manager **não é** auto suficiente ao depositar os registros DOI, é necessário a intervenção humana para inicializar o processo de registro. Após instalação do DOI Manager o Comando `processing_export_doi` estará disponível a partir da linha de comando, para mais opções execute o comando `processing_export_doi --help`.

Ao configurar o ambiente de `deploy` da aplicação é recomendável que se configure agendadores de execução para o comando `processing_export_doi`.

**ATENÇÃO** :warning: O DOI Manager é dependente dos dados vindos do [`ArticleMeta`](https://github.com/scieloorg/articles_meta/), a execução do comando `processing_export_doi` só deverá acontecer após o `ArticleMeta` estar **ATUALIZADO**. Para mais detalhes sobre *datas e horários de atualização* consulte a pessoa responsável pela infraestrutura.
