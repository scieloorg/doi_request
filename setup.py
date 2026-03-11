import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    README = f.read()

install_requires = [
    'alembic>=1.16,<2',
    'articlemetaapi>=1.26.5',
    'celery[redis]>=5.4,<6',
    'lxml>=5.3,<6',
    'pyramid>=2,<3',
    'pyramid-mako>=1.1.0,<2',
    'psycopg[binary]>=3.2,<4',
    'requests>=2.32,<3',
    'SQLAlchemy>=2,<3',
    'waitress>=3,<4',
    'zope.sqlalchemy>=3,<4',
    'sentry-sdk>=2,<3',
]

setup(
    name="doi_request",
    version="1.5.0",
    description="Tool to manage the DOI registering process",
    long_description=README + '\n',
    long_description_content_type='text/markdown',
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
    maintainer="Fabio Batalha",
    maintainer_email="fabio.batalha@scielo.org",
    url="http://github.com/scieloorg/doi_request",
    packages=[
        "crossref",
        "doi_request",
        "doi_request.models",
        "processing",
        "tasks",
        "utils",
        "xsd",
    ],
    include_package_data=False,
    package_data={
        "doi_request": [
            "locale/doi_request.pot",
            "locale/*/LC_MESSAGES/*.mo",
            "locale/*/LC_MESSAGES/*.po",
            "static/**/*",
            "templates/*.mako",
            "templates/*.html",
        ],
        "xsd": ["*.xsd"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.14",
    ],
    install_requires=install_requires,
    python_requires='>=3.14',
    extras_require={'dev': ['pyramid_debugtoolbar', 'Babel']},
    entry_points={
        'paste.app_factory': [
            'main = doi_request:main',
        ],
        'console_scripts': [
            'processing_export_doi = processing.exportDOI:main',
            'processing_export_id = processing.export2id:main'
        ]
    },
)
