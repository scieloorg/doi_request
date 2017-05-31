#!/usr/bin/env python
import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()
with open(os.path.join(here, 'CHANGES.txt')) as f:
    CHANGES = f.read()

install_requires = [
    'thriftpy==0.3.1',
    'requests==2.11.1',
    'pyramid',
    'pyramid_mako',
    'pyramid_debugtoolbar',
    'waitress',
    'Babel',
    'articlemetaapi',
    'lxml',
    'mongoengine',
    'celery',
    'SQLAlchemy',
    'psycopg2',
    'zope.sqlalchemy',
    'alembic'
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'pytest',
    'pytest-cov',
]


setup(
    name="doi_request",
    version="1.1.0",
    description="Tool to manage the DOI registering process",
    long_description=README + '\n\n' + CHANGES,
    author="SciELO",
    author_email="scielo-dev@googlegroups.com",
    maintainer="Fabio Batalha",
    maintainer_email="fabio.batalha@scielo.org",
    url="http://github.com/scieloorg/processing",
    packages=find_packages(),
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
    # entry_points="""
    # [console_scripts]
    # processing_export_doi=processing.exportDOI:main
    # main=doi_request:main
    # """
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
