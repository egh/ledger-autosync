# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ledger-autosync',
    version="0.3.5",
    description="Automatically sync your bank's data with ledger",
    long_description=long_description,
    author='Erik Hetzner',
    author_email='egh@e6h.org',
    url='https://gitlab.com/egh/ledger-autosync',
    license='GPLv3',

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Topic :: Office/Business :: Financial :: Accounting',
        'Topic :: Office/Business :: Financial :: Investment',
        'Topic :: Office/Business :: Financial'
    ],

    keywords='ledger accounting',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    install_requires=[
        'setuptools>=26',
        'ofxclient',
        'ofxparse>=0.14',
        'BeautifulSoup4',
        'fuzzywuzzy'
    ],

    extras_require={
        'test': ['nose>=1.0', 'mock']
    },

    entry_points={
        'console_scripts': [
            'ledger-autosync = ledgerautosync.cli:run',
            'hledger-autosync = ledgerautosync.cli:run'
        ]
    },

    test_suite = 'nose.collector'
)
