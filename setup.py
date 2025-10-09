#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# setup.py -- Butterfly-Backup
#
#     Copyright (C) 2025 Matteo Guadrini <matteo.guadrini@hotmail.it>
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from setuptools import setup

with open("README.md") as rme:
    long_description = rme.read()

setup(
    name="Butterfly-Backup",
    py_modules=["bb", "utility"],
    version="1.21.0",
    url="https://matteoguadrini.github.io/Butterfly-Backup/",
    project_urls={
        "Documentation": "https://butterfly-backup.readthedocs.io/en/latest/",
        "GitHub Project": "https://github.com/MatteoGuadrini/Butterfly-Backup",
        "Issue Tracker": "https://github.com/MatteoGuadrini/Butterfly-Backup/issues",
    },
    install_requires=["pansi==2020.7.3", "fabric==3.2.2"],
    license="GNU General Public License v3.0",
    keywords=[
        "backup",
        "archive",
        "restore",
        "rsync",
        "catalog",
        "list",
        "config",
        "export",
        "mirror",
        "incremental",
        "differential",
        "clone",
        "copy",
    ],
    author="Matteo Guadrini",
    author_email="matteo.guadrini@hotmail.it",
    maintainer="Matteo Guadrini",
    maintainer_email="matteo.guadrini@hotmail.it",
    description="Butterfly Backup is a simple command line wrapper of rsync.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    entry_points={"console_scripts": ["bb = bb:main"]},
    python_requires=">=3.8",
)
