#!/usr/bin/env python
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md')) as f:
    README = f.read()

install_requires = [
    'requests',
    'pyramid',
    'pyramid_mako',
    'waitress',
    'articlemetaapi',
    'lxml',
    'celery[redis]',
    'SQLAlchemy',
    'psycopg2',
    'zope.sqlalchemy',
    'alembic',
]

tests_require = [
]


setup(
    name="doi_request",
    version="1.4.0",
    description="Tool to manage the DOI registering process",
    long_description=README + '\n',
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
    maintainer="Fabio Batalha",
    maintainer_email="fabio.batalha@scielo.org",
    url="http://github.com/scieloorg/doi_request",
    packages=find_packages(exclude=["alembic", "*.tests", "*.tests.*", "tests.*", "tests"]),
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
    ],
    dependency_links=[],
    message_extractors={
        'doi_request': [
            ('**.py', 'python', None),
            ('templates/**.html', 'mako', None),
            ('templates/**.mako', 'mako', None),
            ('static/**', 'ignore', None)
        ]
    },
    tests_require=tests_require,
    test_suite='tests',
    install_requires=install_requires,
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
