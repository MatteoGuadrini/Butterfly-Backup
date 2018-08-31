#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# setup.py -- Butterfly-Backup
#
#     Copyright (C) 2018 Matteo Guadrini <matteo.guadrini@hotmail.it>
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

import shutil
import os
import platform

if platform.system() == 'Darwin':
    # Mac OS installation
    bb_path = '/Applications/bb'
    bb_core = 'bb.py'
    bb_utility = 'utility.py'
    bb_command = '/usr/bin/bb'
else:
    # Unix installation
    bb_path = '/opt/bb'
    bb_core = 'bb.py'
    bb_utility = 'utility.py'
    bb_command = '/usr/bin/bb'

if not os.path.exists(bb_path):
    os.mkdir(bb_path)

shutil.copyfile(bb_core, os.path.join(bb_path, bb_core))
shutil.copyfile(bb_utility, os.path.join(bb_path, bb_utility))
os.chmod(os.path.join(bb_path, bb_core), mode=0o755)
if not os.path.exists(bb_command):
    os.symlink(os.path.join(bb_path, bb_core), bb_command)
