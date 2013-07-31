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
    'git+https://github.com/SpazioDati/dewiki.git@131f834089fa213152fd8edd4ebd206a7e53d581#egg=dewiki-0.1.0',
    'git+https://github.com/SpazioDati/DataTXT-querist.git@b60823d03835d15da6063a3d512b685b2e024168#egg=datatxt_querist-0.1',
    'git+https://github.com/SpazioDati/DBpedia-querist.git@d21e4f65f996305cb231ad4cac9bb341d65f05eb#egg=dbpedia_querist-0.1',
    'git+https://github.com/SpazioDati/Wikipedia-Template-Parser.git@4c943f041fd010c9645f338090b76ebd41d07f6b#egg=wikipedia_template_parser',
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
