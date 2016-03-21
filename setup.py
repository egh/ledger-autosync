from setuptools import setup, find_packages

with open('README.rst') as file:
    long_description = file.read()

setup(name='ledger-autosync',
      version="0.2.4",
      description="Automatically sync your bank's data with ledger",
      long_description=long_description,
      classifiers=[
          "Operating System :: OS Independent",
          "Programming Language :: Python",
      ],
      author='Erik Hetzner',
      author_email='egh@e6h.org',
      url='https://bitbucket.org/egh/ledger-autosync',
      packages=find_packages(exclude=[
          'tests']),
      entry_points={
          'console_scripts': [
              'ledger-autosync = ledgerautosync.cli:run',
              'hledger-autosync = ledgerautosync.cli:run'
          ]
      },
      install_requires=[
          # Latest ofxclient is not working.
          # TODO: Look into it
          "ofxclient<2.0.0",
          "ofxparse>=0.14",
          # 4.4.0 complains about the way ofxparse uses it
          "BeautifulSoup4<4.4.0",
      ],
      setup_requires=['nose>=1.0',
                      'mock'],
      test_suite = 'nose.collector'
      )
