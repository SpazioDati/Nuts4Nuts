#!/usr/bin/env python

import os
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

if sys.argv[-1] == "publish":
    os.system("python setup.py sdist upload")
    sys.exit()

required = [
    'requests==1.2.0',
    'PyBrain==0.3',
    'dewiki==0.1.0',
    'datatxt_querist==0.1',
    'dbpedia_querist==0.1',
]
dependency_links = [
    'git+https://github.com/SpazioDati/dewiki.git#egg=dewiki-0.1.0',
    'git+https://github.com/SpazioDati/DataTXT-querist.git#egg=datatxt_querist-0.1',
    'git+https://github.com/SpazioDati/DBpedia-querist.git#egg=dbpedia_querist-0.1',
]

setup(
    name='nuts4nuts',
    version='0.1',
    description='Simple library to infer the municipality name from a Wikipedia abstract',
    author='Cristian Consonni',
    author_email='consonni@fbk.eu',
    url='https://github.com/SpazioDati/Nuts4nuts',
    packages=['nuts4nuts'],
    install_requires=required,
    dependency_links=dependency_links,
    license='MIT',
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Topic :: Internet',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ),
)
