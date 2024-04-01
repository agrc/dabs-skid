#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
setup.py
A module that installs the SKIDNAME skid as a module
"""
from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

#: Load version from source file
version = {}
with open('src/dabs/version.py') as fp:
    exec(fp.read(), version)

setup(
    name='dabs',
    version=version['__version__'],
    license='MIT',
    description='Update the DABS data from SOURCE via GCF',
    author='UGRC',
    author_email='ugrc@utah.gov',
    url='https://github.com/eneemann/dabs-skid',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=True,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Topic :: Utilities',
    ],
    project_urls={
        'Issue Tracker': 'https://github.com/eneemann/python/issues',
    },
    keywords=['gis'],
    install_requires=[
        'ugrc-palletjack>=4.1,<4.4',
        'agrc-supervisor==3.0.*',
    ],
    extras_require={
        'tests': [
            'pylint-quotes~=0.2',
            'pylint>=2.11,<4.0',
            'pytest-cov>=3,<6',
            'pytest-instafail~=0.4',
            'pytest-isort>=2,<5',
            'pytest-pylint~=0.18',
            'pytest-watch~=4.2',
            'pytest>=6,<9',
            'yapf~=0.31',
            'functions-framework',
        ]
    },
    setup_requires=[
        'pytest-runner',
    ],
    entry_points={'console_scripts': [
        'dabs = dabs.main:main',
    ]},
)
