"""Project's setup"""
import os

import comoda.yaml
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "omnia", "APPNAME")) as f:
    __appname__ = f.read().strip()

with open(os.path.join(here, "omnia", "VERSION")) as f:
    __version__ = f.read().strip()

with open(os.path.join(here, "README.md")) as f:
    long_description = f.read()

environment = comoda.yaml.load(os.path.join(here, "environment.yml"))
required = environment["dependencies"][2]["pip"]

extra_files = [
    os.path.join(here, "environment.yml"),
    os.path.join(here, "omnia", "VERSION"),
    os.path.join(here, "omnia", "APPNAME"),
    os.path.join(here, "config", "config.yaml"),
]

setup(
    name=__appname__,
    version=__version__,
    description="Omnia",
    long_description=long_description,
    long_description_content_type="text/markdown",
    # The project's main homepage.
    url="https://git...",
    # Author details
    author="Gianmauro Cuccuru",
    author_email="gianmauro.cuccuru@fht.org",
    # Choose your license
    license="GPLv3",
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        # Indicate who your project is intended for
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    # What does your project relate to?
    keywords="bioinformatics",
    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(),
    package_data={"": extra_files},
    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=required,
    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        "console_scripts": [
            "omnia=omnia.main:main",
        ],
    },
)
