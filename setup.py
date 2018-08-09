#!/usr/bin/python3

import shutil
import os

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
