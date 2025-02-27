# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name="bot",
    version="0.1",
    packages=find_packages("src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    test_suite="tests"
)