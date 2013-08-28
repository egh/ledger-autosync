from setuptools import setup, find_packages

setup(name='ledger-autosync',
      version="0.1",
      description="Automatically sync your bank's data with ledger",
      long_description="""
ledger-autosync is a program to pull down transactions from your
bank and create `ledger <http://ledger-cli.org/>`_ transactions for
them. It is designed to only create transactions that are not already
present in your ledger files. This should make it comparable to some
of the automated synchronization features available in products like
GnuCash, Mint, etc.""",
      classifiers=[
          "Development Status :: 4 - Alpha",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
      ],
      author='Erik Hetzner',
      author_email='egh@e6h.org',
      url='https://bitbucket.org/egh/ledger-autosync',
      packages=find_packages(exclude=[
          'tests']),
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'ledger-autosync = ledgerautosync.cli:run'
          ]
      },
      install_requires=[
          "ofxclient",
      ],
      test_suite='tests',
      )
