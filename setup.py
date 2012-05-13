from setuptools import setup, find_packages
import os

version = '0.0.2'

setup(name='badgerproxy',
      version=version,
      url="http://www.isotoma.com/",
      description="badgerproxy",
      long_description=open("README.rst").read(),
      author="Isotoma Limited",
      author_email="john.carr@isotoma.com",
      license="Apache Software License",
      classifiers = [
          "Intended Audience :: System Administrators",
          "Operating System :: POSIX",
          "License :: OSI Approved :: Apache Software License",
      ],
      packages=find_packages(exclude=['ez_setup']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'setuptools',
          'yay >= 0.0.24',
          'missingbits',
      ],
      entry_points = {
        "console_scripts": [
            'badgerproxyctl=badgerproxy.scripts.badgerproxyctl:run',
            'badgerproxy=badgerproxy.scripts.badgerproxy:run',
            ],
        "zc.buildout": [
            'default = badgerproxy.recipe:Recipe',
            ],
        }
      )

