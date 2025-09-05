<img src="https://butterfly-backup.readthedocs.io/en/latest/_static/bb_logo.svg" alt="Butterfly Backup" align="right" width="150"/> Butterfly Backup
======

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/7fc47024f17f4dffa3be08a7a5ab31bd)](https://app.codacy.com/app/MatteoGuadrini/Butterfly-Backup?utm_source=github.com&utm_medium=referral&utm_content=MatteoGuadrini/Butterfly-Backup&utm_campaign=Badge_Grade_Dashboard)
[![CircleCI](https://circleci.com/gh/MatteoGuadrini/Butterfly-Backup.svg?style=svg)](https://circleci.com/gh/MatteoGuadrini/Butterfly-Backup)

## Introduction
Butterfly Backup is a modern backup program that can back up your files:

* from **Linux**, **BSD**, **Mac** and **Windows** (through [cygwin](https://www.cygwin.com/))
* **easily**, being a single executable that you can run without a server or complex setup
* **effectively**, only transferring the parts that actually changed in the files you back up, in four mode (_full_, _incremental_, _differential_ and _mirror_)
* **verifiably**, store all backup in a readable catalog also through file system
* **speedly**, parallelizing all backup, restore and export operations
* **securely**, exporting, archiving and applying retention
* **freely** - entirely free to use and completely open source

## Test
If you want to try or test Butterfly Backup before installing it, run the test:
```console
$ git clone https://github.com/MatteoGuadrini/Butterfly-Backup.git
$ cd Butterfly-Backup
$ bash test_bb.py
...
[92512a6e-506e-11eb-b747-2ba55b805ea5]
type = full
path = /tmp/bb_repo/localhost/2024_01_06__23_28
name = localhost
os = unix
timestamp = 2024-01-06 23:28:59
start = 2024-01-06 23:28:59
end = 2024-01-06 23:29:04
status = 0
```

## Installation
Install Butterfly Backup is very simple; run this:
```bash
git clone https://github.com/MatteoGuadrini/Butterfly-Backup.git
cd Butterfly-Backup
sudo python3 setup.py install -f # -f is for upgrade
# or
sudo pip install . --upgrade
bb --help
```

## Quickstart
A short demo of Butterfly Backup:
```bash
bb backup --computer host1 --destination /nas/mybackup --data user config --type macos --mode full
```
or with short option:
```bash
bb backup -c host1 -d /nas/mybackup -D user config -t macos -m full
```
So we created a first _full_ backup, on a _macos_ machine, considering the folders _User_ -> /Users and _Config_ -> /private/etc in the destination _/nas/mybackup_

> [!NOTE]  
> If you do not specify the user, Butterfly Backup will assume that the source and the destination know the same user; for example, I start the backup with the above command and my user is calling _arthur_, he will use the latter to log in to host1.

Now that we have our first full backup, we can run _incremental_ for the next few times.
```bash
bb backup --computer host1 --destination /nas/mybackup --data user config --type macos
```
or with short option:
```bash
bb backup -c host1 -d /nas/mybackup -D user config -t macos

```
> [!NOTE]  
> Incremental mode performs a full backup when they have not been done before.

Before starting any restore, you need to understand what kind of data and in what time period you have to start.
So, let's start checking our backups into the catalog, with this command:
```bash
bb list --catalog /nas/mybackup
```

The result will be the following:

```bash
BUTTERFLY BACKUP CATALOG

Backup id: f65e5afe-9734-11e8-b0bb-005056a664e0
Hostname or ip: host1
Timestamp: 2024-08-03 17:50:36

Backup id: 4f2b5f6e-9939-11e8-9ab6-005056a664e0
Hostname or ip: host1
Timestamp: 2024-08-06 07:26:46

Backup id: cc6e2744-9944-11e8-b82a-005056a664e0
Hostname or ip: host1
Timestamp: 2024-08-06 08:49:00
```

Select (copy) _Backup id_ when you want restore a backup.
For exit, press `q`.

Now, run this command for more detail (for example, try the first):

```bash
bb list --catalog /nas/mybackup --backup-id f65e5afe-9734-11e8-b0bb-005056a664e0
```
The result will be the following:
```bash
Backup id: f65e5afe-9734-11e8-b0bb-005056a664e0
Hostname or ip: host1
Type: full
Timestamp: 2024-08-03 17:50:36
Start: 2024-08-03 17:50:36
Finish: 2024-08-03 18:02:32
OS: macos
ExitCode: 0
Path: /nas/mybackup/host1/2024_08_03__17_50
List: etc
Users
```

Now that we are sure that the selected backup is what we want (both in data and on date), run this command:

```bash
bb restore --computer host1 --catalog /nas/mybackup --backup-id f65e5afe-9734-11e8-b0bb-005056a664e0
```
So we have restored the data saved on the date indicated in our _host1_.

## Web interface: Butterfly-Backup-Web

In this [repository](https://github.com/MatteoGuadrini/butterfly-backup-web) you find a simple web interface of **Butterfly Backup**.

Copy this snippet for a rapid start

```console
# Installation
git clone https://github.com/MatteoGuadrini/butterfly-backup-web.git
cd butterfly-backup-web
pip install . --upgrade

# Modify this variable for your catalog path
export BB_CATALOG_PATH=/backup

# Use bbweb command line
bbweb migrate
bbweb createsuperuser
bbweb runserver 0.0.0.0:80
```

## 3-2-1 rule

With Butterfly Backup you can apply _3-2-1 rule_ (Keep three copies of your data on two different types of media, with one copy offsite) in only 4 lines:

```bash
CATALOG="/nas/mybackup"
bb backup --computer host1 --destination $CATALOG --data user config --type macos; BCKID="$(bb list --catalog $CATALOG --last --computer host1 --only-id)"
bb export --catalog $CATALOG --backup-id "$BCKID" --destination /mnt/other_backup/
# attach you USB drive on your host1...
bb restore --computer host1 --catalog $CATALOG --backup-id "$BCKID" --root-dir /usb/path   # on Windows /cygdrive/d/
```

Schedule on your own this script in your backup server and you have applied the rule.

## Documentation
[Manual of Butterfly Backup](https://Butterfly-Backup.readthedocs.io/en/latest/) or run help:
```bash
bb --help
```

## Open source
Butterfly Backup is a open source project. Any contribute, It's welcome.

**A great thanks**.

For donations, press this

For me

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.me/guos)

For [Telethon](http://www.telethon.it/)

The Telethon Foundation is a non-profit organization recognized by the Ministry of University and Scientific and Technological Research.
They were born in 1990 to respond to the appeal of patients suffering from rare diseases.
Come today, we are organized to dare to listen to them and answers, every day of the year.

[Adopt the future](https://www.ioadottoilfuturo.it/)

## Acknowledgments

Thanks to Mark Lutz for writing the _Learning Python_ and _Programming Python_ books that make up my python foundation.

Thanks to Kenneth Reitz and Tanya Schlusser for writing the _The Hitchhiker’s Guide to Python_ books.

Thanks to Dane Hillard for writing the _Practices of the Python Pro_ books.

Special thanks go to my wife, who understood the hours of absence for this development. 
Thanks to my children, for the daily inspiration they give me and to make me realize, that life must be simple.

Thanks Python!