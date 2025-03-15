#!/bin/bash

# Unit testing for Butterfly Backup system
echo "Python3 is installed?"

if [ -n "/bin/python3" ]; then
	echo "Python3 exists!"
	python3 -m venv venv
else
	exit 1
fi

# Add execute permission on bb.py
echo "Activate Python venv"

. venv/bin/activate

echo "Install Butterfly backup into venv"
venv/bin/pip install .

# Create enviroment for first backup
repo=/tmp/bb_repo
if [ -d $repo ]; then
	rm -rf /tmp/bb_*
fi
echo "Create enviroment for first backup"
mkdir $repo
echo "Create Butterfly Backup folder $repo"
data=/tmp/bb_client
mkdir $data
echo "Create client folder $data"
touch $data/file.txt $data/file.docx $data/file.xlsx

# Start first full backup
echo "Start full backup"
echo "Select operating system [unix, macos, windows]: "
read os

if [ "$os" = "unix" ]; then
	os="unix"
elif [ "$os" = "macos" ]; then
	os="macos"
elif [ "$os" = "windows" ]; then
	os="windows"
else
	echo "ERROR: available only unix, macos, windows"
	exit 2
fi

echo "Test backup"
venv/bin/bb backup --computer localhost --destination $repo --custom-data $data --type $os --verbose --log --retention 1 1

# Test if backup was created
backup=$repo/localhost
if [ -d $backup ]; then
	echo "Backup was created $backup"
else
	echo "Backup failed"
	exit 3
fi

# Test export
echo "Test export"
exp_data="/tmp/bb_exp"
mkdir $exp_data

venv/bin/bb export --catalog $repo --all --destination $exp_data --verbose --log

# Test if restore was performed
if [ -f "$exp_data/.catalog.cfg" ]; then
	echo "Export was performed"
else
	echo "Export failed"
	exit 3
fi

# Check catalog
echo "Check catalog: $ cat $repo/.catalog.cfg"
cat $repo/.catalog.cfg
