#!/usr/bin/env python

import os
from setuptools import setup

README = """
See the README on `GitHub
<https://github.com/uw-it-aca/canvas_training_provisioner>`_.
"""

version_path = 'training_provisioner/VERSION'
VERSION = open(os.path.join(os.path.dirname(__file__), version_path)).read()
VERSION = VERSION.replace("\n", "")

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='Canvas Training Provisioner',
    version=VERSION,
    packages=['training_provisioner'],
    include_package_data=True,
    install_requires=[
        'django~=5.2',
        'django-storages[google]',
        'djangorestframework~=3.14',
        'uw-restclients-canvas~=1.2',
    ],
    license='Apache License, Version 2.0',
    description=('An application to manage Training course and enrollment '
                 'Canvas provisioning to Canvas'),
    long_description=README,
    url='https://github.com/uw-it-aca/canvas-training-provisioner',
    author="UW-IT Student & Educational Technology Services",
    author_email="aca-it@uw.edu",
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
