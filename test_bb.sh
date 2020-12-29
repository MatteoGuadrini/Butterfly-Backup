#!/bin/bash

# Unit testing for Butterfly Backup system
echo "Python3 is installed?"

if [ -n "/bin/python3" ]; then
	echo "Python3 exists!"
else
	exit 1
fi

# Add execute permission on bb.py
echo "Add execute permission on bb.py"

chmod +x bb.py

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
echo "Select operating system [Unix, MacOS, Windows]: "
read os

if [ "$os" = "Unix" ]; then
	os="Unix"
elif [ "$os" = "MacOS" ]; then
	os="MacOS"
elif [ "$os" = "Windows" ]; then
	os="Windows"
else
	echo "ERROR: available only Unix, MacOS, Windows"
	exit 2
fi

echo "Test backup"
python3 bb.py backup --computer localhost --destination $repo --custom-data $data --type $os --verbose --log

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

python3 bb.py export --catalog $repo --all --destination $exp_data --verbose --log

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

