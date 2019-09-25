#!/usr/bin/env python
from setuptools import setup

setup(
      name="tap-pagerduty",
      version="0.1.0",
      description="Singer.io tap for extracting pagerduty data",
      author="Stitch",
      url="http://singer.io",
      classifiers=["Programming Language :: Python :: 3 :: Only"],
      py_modules=["tap_pagerduty"],
      install_requires=[
            "singer-python>=5.0.12",
            "requests",
            "pendulum"
      ],
      entry_points="""
    [console_scripts]
    tap-pagerduty=tap_pagerduty:main
    """,
      packages=["tap_pagerduty"],
      package_data = {
            "schemas": ["tap_pagerduty/schemas/*.json"]
      },
      include_package_data=True,
)
