![Greta oto](img/bb.png)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/7fc47024f17f4dffa3be08a7a5ab31bd)](https://app.codacy.com/app/MatteoGuadrini/Butterfly-Backup?utm_source=github.com&utm_medium=referral&utm_content=MatteoGuadrini/Butterfly-Backup&utm_campaign=Badge_Grade_Dashboard)

# Butterfly Backup: presentation
**The plan is great when the backup plan is excellent!**

## What is that?
Butterfly Backup is a _simple_ command line wrapper of rsync for _complex_ task, written in python.

## Why butterfly?
Butterfly Backup exploits the potential of rsync with maximum simplicity, and more.

## What can I do?
With Butterfly Backup I can perform single or group backups (Full, Incremental and Mirror), restore and archive old backups.

## How can you do it?
Naturally through the synergy of rsync and OpenSSH technology.

## Which platforms support?
Butterfly Backup run on Linux, BSD, MacOSX and Windows(with cygwin, see config [docs](https://Butterfly-Backup.readthedocs.io/en/latest/))

## Real uses
This list consists of only a few examples; applications can be endless:
* Backing up a folder where I store my photos over the years;
* Log's backup of one or more servers;
* Backup of users of one or more machines;
* Backup system config of much servers;
* Create a backup snapshot of the my laptop;
* Create a central server than backupping client and server
* Backup a entire file server, incrementally;

## Real possibilities
- Configuration for silently backup
- All backup are organized into a catalog
- List single or all backup by the catalog
- Backup single PC, with Full,Incremental,Differential and Mirror mode;
- Backup more PCs, with Full,Incremental,Differential and Mirror mode (with parallelism algorithm);
- Backup custom folder or predefined data (User,Config,Application,System,Log)
- Restore backup on the same PC
- Restore backup in other PC
- Restore backup in other operating system
- Apply retention policy to delete old backup
- Archive old backup in other file system or same (zip backup folder)


# Butterfly Backup: in action
**Transform rsync in a powerfully backup/restore tool**

## Operation
All operation of Butterfly Backup are _server to client_, agent-less.
This means that all commands must be executed by the backup server. Of course, nothing prevents the backup server from being itself (localhost).

To see all the operations and more examples, see the [docs](https://Butterfly-Backup.readthedocs.io/en/latest/).

## Installation
Install Butterfly Backup is very simple; run this:
```bash
git clone https://github.com/MatteoGuadrini/Butterfly-Backup.git
cd Butterfly-Backup
sudo python3 setup.py
bb --help
```

### Backup machine
Backup a single PC or server is a everyday task.
But most of the data may not change in the various backups made;
then, in these cases, an incremental backup is needed.
Butterfly Backup natively supports incremental and differential backups, starting from a full.
In this case, the first backup to be performed on the machine will be as follows:
```bash
bb backup --computer pc1 --destination /nas/mybackup --data User Config --type MacOS --mode Full
```
or with short option:
```bash
bb backup -c pc1 -d /nas/mybackup -D User Config -t MacOS -m Full
```
So we created a first _Full_ backup, on a _MacOS_ machine, considering the folders _User_ -> /Users and _Config_ -> /private/etc in the destination _/nas/mybackup_
> **Note**: if you do not specify the user, Butterfly Backup will assume that the source and the destination know the same user; for example, I start the backup with the above command and my user is calling _arthur_, he will use the latter to log in to pc1.

Now that we have our first Full backup, we can run _incremental_ for the next few times.
```bash
bb backup --computer pc1 --destination /nas/mybackup --data User Config --type MacOS
```
or with short option:
```bash
bb backup -c pc1 -d /nas/mybackup -D User Config -t MacOS
```
> **Note**: Incremental mode performs a Full backup when they have not been done before.

### Restore machine
Before starting any restore, you need to understand what kind of data and in what time period you have to start.
So, let's start checking our backups, with this command:
```bash
bb list --catalog /nas/mybackup
```
The result will be the following:
```bash
BUTTERFLY BACKUP CATALOG

Backup id: f65e5afe-9734-11e8-b0bb-005056a664e0
Hostname or ip: pc1
Timestamp: 2018-08-03 17:50:36

Backup id: 4f2b5f6e-9939-11e8-9ab6-005056a664e0
Hostname or ip: pc1
Timestamp: 2018-08-06 07:26:46

Backup id: cc6e2744-9944-11e8-b82a-005056a664e0
Hostname or ip: pc1
Timestamp: 2018-08-06 08:49:00
```
Select (copy) _Backup id_ when you want restore a backup.
For exit, press `q`
Now, run this command for more detail (for example, try the first):
```bash
bb list --catalog /nas/mybackup --backup-id f65e5afe-9734-11e8-b0bb-005056a664e0
```
The result will be the following:
```bash
Backup id: f65e5afe-9734-11e8-b0bb-005056a664e0
Hostname or ip: pc1
Type: Full
Timestamp: 2018-08-03 17:50:36
Start: 2018-08-03 17:50:36
Finish: 2018-08-03 18:02:32
OS: MacOS
ExitCode: 0
Path: /nas/mybackup/pc1/2018_08_03__17_50
List: etc
Users
```
Now that we are sure that the selected backup is what we want (both in data and on date), run this command:
```bash
bb restore --computer pc1 --catalog /nas/mybackup --backup-id f65e5afe-9734-11e8-b0bb-005056a664e0
```
So we have restored the data saved on the date indicated in our _pc1_.

### Other operation
With Butterfly Backup, you can perform Full, Incremental and Mirror backups, applying retention or archive rules;
you can activate the log function, so as to track any operation over time and/or increase verbosity.
Bulk backup operations can be performed using a simple text file, formatted in a list.
Is possible create, by means of openssh operations, a configuration and copy them into the machines impacted by the backup without causing the machine to request the password (key exchange).
For all this, [Read the Docs](https://Butterfly-Backup.readthedocs.io/en/latest/) or run help:
```bash
bb --help
```

# Butterfly Backup: supports

## One more thing
The name butterfly, is born precisely because agent-less; like a butterfly takes the pollen from a flower and brings it elsewhere.
A backup or restore is performed without any iteration responsibility on the part of the final machine.
The performances are not altered.
While all the operations of Butterfly Backup are carried out, the impacted machine can continuously work with peace of mind.

## Follow the project
See the new features in development through this [link](https://tree.taiga.io/project/matteoguadrini-butterfly-backup/kanban).

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

<a href="https://dona.telethon.it/it/dona-ora"> <img src="http://www.telethon.it/sites/all/themes/telethon/images/svg/logo.svg" alt="Telethon" title="Telethon" width="200" height="104" /> </a>
