#!/usr/bin/env python
from setuptools import setup, find_packages
import os, re

PKG='txsimplegeo.shared'
VERSIONFILE = os.path.join('txsimplegeo', 'shared', '_version.py')
verstr = "unknown"
try:
    verstrline = open(VERSIONFILE, "rt").read()
except EnvironmentError:
    pass # Okay, there is no version file.
else:
    MVSRE = r"^manual_verstr *= *['\"]([^'\"]*)['\"]"
    mo = re.search(MVSRE, verstrline, re.M)
    if mo:
        mverstr = mo.group(1)
    else:
        print "unable to find version in %s" % (VERSIONFILE,)
        raise RuntimeError("if %s.py exists, it must be well-formed" % (VERSIONFILE,))
    AVSRE = r"^auto_build_num *= *['\"]([^'\"]*)['\"]"
    mo = re.search(AVSRE, verstrline, re.M)
    if mo:
        averstr = mo.group(1)
    else:
        averstr = ''
    verstr = '.'.join([mverstr, averstr])

setup_requires = ['setuptools_trial']
tests_require = ['mock', 'setuptools_trial']

# trialcoverage is an optional way to get code-coverage
# results. Uncomment the following and run "python setup.py trial
# --reporter=bwverbose-coverage -s simplegeo.shared.test".
# tests_require.extend(['setuptools_trial', 'trialcoverage'])

# As of 2010-11-22 neither of the above options appear to work to
# generate code coverage results, but the following does:
# rm -rf ./.coverage* htmlcov ; coverage run --branch  --include=txsimplegeo/* setup.py trial ; coverage html

data_fnames=[ 'COPYING.SPL.txt', 'COPYING.GPL', 'COPYING.TGPPL.html', 'README.rst' ]

# In case we are building for a .deb with stdeb's sdist_dsc command, we put the
# docs in "share/doc/python-$PKG".
doc_loc = "share/doc/" + PKG
data_files = [(doc_loc, data_fnames)]

setup(name=PKG,
      version=verstr,
      description="Twisted library for interfacing with SimpleGeo's API",
      long_description=open('README.rst').read(),
      author="Zooko Wilcox-O'Hearn",
      author_email="zooko@simplegeo.com",
      url="http://github.com/simplegeo/python-txsimplegeo.shared",
      packages = find_packages(),
      include_package_data=True,
      data_files=data_files,
      license = "MIT License",
      install_requires=['pyutil >= 1.7.9'],
      keywords="simplegeo",
      zip_safe=False, # actually it is zip safe, but zipping packages doesn't help with anything and can cause some problems (http://bugs.python.org/setuptools/issue33 )
      namespace_packages = ['txsimplegeo'],
      test_suite='txsimplegeo.shared.test',
      setup_requires=setup_requires,
      tests_require=tests_require)
