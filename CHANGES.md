# Release notes

## 1.18.0
Mar 09, 2025
* Add **--links** argument into _export_, _backup_ and _restore_ actions
* Fix check of retention arguments

## 1.17.0
Feb 24, 2025
* Add **--keytype** argument
* Add **--acl** argument into _export_ action

## 1.16.0
Feb 04, 2025
* Add **--explain-error** argument
* Add **--only-id** argument into _list_ action
* Fix _ignore-times_ option into rsync in _restore_ action

## 1.15.0
Jan 18, 2025
* Add **--acl** argument in _restore_ action
* Add **--link** argument in _export_ action
* Add info word in normal print output

## 1.14.0
Jan 09, 2025
* Add **--root-dir** argument in _restore_ action
* Add warning on exit command if rsync error is `23` or `24`
* Add more check for ssh connection
* Unlink _last_backup_ folder if retention is applied
* Fix _system_ key into **compose_restore_src_dst** function

## 1.13.0
Jan 02, 2025
* Fix return of **get_last_backup** function for incremental and differential backup, refs #7

## 1.12.0
May 24, 2024
* Add **--no-color** argument

## 1.11.0
Feb 15, 2024
* Add **--file-data** argument in *backup* action
* Add **--force** argument in *every* action
* Add *confirm* function to every potentially destrucive actions
* Fix returns of *get_last_backup* function
* Fix **--version** argument

## 1.10.0
Jul 1, 2023
* Add **report_issue** function
* Add **get_bckid** function
* Add **--files** argument in *restore* action
* Add **--delete-backup** argument in *config* action
* Add lowercase support on command line
* Fix **check_rsync** function to include *sshconfig* file
* Fix required to *action* subparser
* Fix check for restore empty folders
* Fix create folder in export action if destination doesn't exists

## 1.9.0
Jun 7, 2023
* Refactoring _setup.py_
* Add **main** function
* Add **pansi** package for coloring output
* Fix **list** command
* Fix format modules with ruff

## 1.8.0
Sep 2, 2019
* Add --start-from to backup action
* Add --detail to list action
* Add --all param to export
* Fix restore for windows enviroment

## 1.7.0
Jul 25, 2019
* Add --delete-host/-D parameter to config
* Add --clean/-c parameter to config
* Add --exclude/-E to backup and restore

## 1.6.0
Jun 20, 2019
* Add second argument of --retention param
* Add param --bwlimit, than specify bandwidth limit
* Add docstring in script
* Add --ssh-port parameter

## 1.5.0
May 17, 2019
* Add --rsync custom path option
* Add config function --init; reset catalog backup file

## 1.4.0
Jan 8, 2019
* Add one-line option in list function
* Add Differential backup mode
* Add Code Of Conduct
* Add man page into command line

## 1.3.0
Oct 23, 2018
* Add list archived backups only
* Add list cleaned backups only
* Add dry-run mode
* Fix documentation and change theme

## 1.2.0
Oct 5, 2018
* Add last option for restore mode
* Add mirror option for restore mode

## 1.1.0
Aug 31, 2018
* Add timeout option
* Fix documentation #1 .Thanks Jack

## 1.0.0
Aug 9, 2018
### A butterfly is born from the chrysalis...welcome Butterfly Backup

* Configuration for silently backup
* All backup are organized into a catalog
* List single or all backup by the catalog
* Backup single PC, with Full,Incremental and Mirror mode;
* Backup more PCs, with Full,Incremental and Mirror mode (with parallelism algorithm);
* Backup custom folder or predefined data (User,Config,Application,System,Log)
* Restore backup on the same PC
* Restore backup in other PC
* Restore backup in other operating system
* Apply retention policy to delete old backup
* Archive old backup in other file system or same (zip backup folder)