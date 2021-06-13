# Always prefer setuptools over distutils
# To use a consistent encoding
from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, "README.rst"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="ledger-autosync",
    version="1.0.2",
    description="Automatically sync your bank's data with ledger",
    long_description=long_description,
    author="Erik Hetzner",
    author_email="egh@e6h.org",
    url="https://gitlab.com/egh/ledger-autosync",
    license="GPLv3",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.5",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Office/Business :: Financial",
    ],
    keywords="ledger accounting",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=[
        "setuptools>=26",
        "ofxclient",
        "ofxparse @ https://github.com/jseutter/ofxparse/tarball/3236cfd96434feb6bc79a8b66f3400f18e2ad3c4",
    ],
    extras_require={"test": ["pytest"]},
    entry_points={
        "console_scripts": [
            "ledger-autosync = ledgerautosync.cli:run",
            "hledger-autosync = ledgerautosync.cli:run",
        ]
    },
)
