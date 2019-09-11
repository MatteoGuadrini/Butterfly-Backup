#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# bb.py -- Butterfly-Backup
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
"""
NAME
    Butterfly Backup - backup/restore/archive tool , agentless

DESCRIPTION
    Butterfly Backup is a simple command line wrapper of rsync for complex task, written in python

SYNOPSIS
    bb [ACTION] [OPTIONS]

    bb [-h] [--verbose] [--log] [--dry-run] [--version]
              {config,backup,restore,archive,list,export} ...

OPTIONS
    action:
      Valid action

      {config,backup,restore,archive,list,export}
                            Available actions
        config              Configuration options
        backup              Backup options
        restore             Restore options
        archive             Archive options
        list                List options
        export              Export options

EXAMPLES
    Show full help:
        O_O>$ bb --help
"""

import argparse
import configparser
import os
import subprocess
import utility
import time
from multiprocessing import Pool
from utility import print_verbose

# region Global Variables
VERSION = '1.8.0'


# endregion


def print_version(version):
    """
    Print version of Butterfly Backup
    :return: str
    """
    print_verbose(args.verbose, 'Print version and logo')
    if args.verbose:
        print_logo()
    print(utility.PrintColor.BOLD + 'Version: ' + utility.PrintColor.END + version)
    exit()


def print_logo():
    """
    Print logo design
    :return: design of logo
    """
    print(
        '''
                .                   .
    .OMMMM..   .....              ...   ...MNNM$...
 .MNNNNNMM7=?..   ...            ..     ??$MMNNNNDN.
 MNNNMMNN:,:,8N:.. ...        ....   :N8,,,:MNMNMNMM.
.MMNMMM,::,,,DDD?8.....      ......+IDDD,,,:+,MMMNNM.
.MNMDN:$,,,,DDD= .?..  ..   ......??.+DDD,,,,$:MDMNM.
.MMMD::,,INN7N... ..?....   . ..$.. ...N7NN?,,,+DMDM.
 DNM7=~:.  ..8..    .:N... ...M+.    ..8..   :=+$MMD
  NI=,.  .:....M..   ..IZ?NN+O.     .M.. .~.  .,~IM.
 .,N:..+..   .?NNMNDDNZ..?NZ..7NNDNMNN8.   ..?..~M8.
   ,NND... ?D7..       .,?Z?~.       ..$D8....DDD.
     .DDNDN7....       .D???N.       .. .ONDNDD.
      ..$~N.. ,. .. .=....M....=. .  .O ..N~+..
      .??ID.M..... ....., I....... .....M.DII?.
       .?Z..   $.  ....,..?. ..... ..I. ...$I
        .8... ... ?.?O   .?~  .MM.+........O.
        ..I8N....:.N.    +??..  .N 8....NN7.
            ..NOM.. .   .I??.     ..MZN.
                         .?.


                     [GRETA OTO]
        '''
    )


def check_rsync():
    """
    Check if rsync tool is installed
    :return: string
    """
    if not utility.check_tool('rsync'):
        print(utility.PrintColor.RED +
              'ERROR: rsync tool is required!' +
              utility.PrintColor.END +
              """
Red-Hat/CentOS/Fedora:    yum install rsync
Debian/Ubuntu/Mint:       apt-get install rsync
Arch Linux:               aur install rsync
Mac OS X:                 install homebrew; brew install rsync
Windows:                  install Cygwin
""")
        exit()


def dry_run(message):
    """
    Check if dry run mode
    :param message: print message standard output
    :return: boolean
    """
    if args.dry_run:
        print_verbose(True, message)
        return True


def run_in_parallel(fn, commands, limit):
    """
    Run in parallel with limit
    :param fn: function in parallelism
    :param commands: args commands of function
    :param limit: number of parallel process
    """
    # Start a Pool with "limit" processes
    pool = Pool(processes=limit)
    jobs = []

    for command, plog in zip(commands, logs):
        # Run the function
        proc = pool.apply_async(func=fn, args=(command,))
        jobs.append(proc)
        print('Start {0} {1}'.format(args.action, plog['hostname']))
        print_verbose(args.verbose, "rsync command: {0}".format(command))
        utility.write_log(log_args['status'], plog['destination'], 'INFO', 'Start process {0} on {1}'.format(
            args.action, plog['hostname']
        ))
        if args.action == 'backup':
            # Write catalog file
            write_catalog(catalog_path, plog['id'], 'start', utility.time_for_log())

    # Wait for jobs to complete before exiting
    while not all([p.ready() for p in jobs]):
        time.sleep(5)

    # Check exit code of command
    for p, command, plog in zip(jobs, commands, logs):
        if p.get() != 0:
            print(utility.PrintColor.RED + 'ERROR: Command {0} exit with code: {1}'.format(command, p.get()) +
                  utility.PrintColor.END)
            utility.write_log(log_args['status'], plog['destination'], 'ERROR',
                              'Finish process {0} on {1} with error:{2}'.format(args.action, plog['hostname'], p.get()))
            if args.action == 'backup':
                # Write catalog file
                write_catalog(catalog_path, plog['id'], 'end', utility.time_for_log())
                write_catalog(catalog_path, plog['id'], 'status', "{0}".format(p.get()))
                if args.retention and args.skip_err:
                    # Retention policy
                    retention_policy(plog['hostname'], catalog_path, plog['destination'])

        else:
            print(utility.PrintColor.GREEN + 'SUCCESS: Command {0}'.format(command) + utility.PrintColor.END)
            utility.write_log(log_args['status'], plog['destination'], 'INFO',
                              'Finish process {0} on {1}'.format(args.action, plog['hostname']))
            if args.action == 'backup':
                # Write catalog file
                write_catalog(catalog_path, plog['id'], 'end', utility.time_for_log())
                write_catalog(catalog_path, plog['id'], 'status', "{0}".format(p.get()))
                if args.retention:
                    # Retention policy
                    retention_policy(plog['hostname'], catalog_path, plog['destination'])

    # Safely terminate the pool
    pool.close()
    pool.join()


def start_process(command):
    """
    Start rsync commands
    :param command: rsync list command
    :return: command
    """
    fd = get_std_out()
    if fd == 'DEVNULL':
        p = subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif fd == 'STDOUT':
        p = subprocess.call(command, shell=True)
    else:
        p = subprocess.call(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p


def get_std_out():
    """
    Return stdout and stderr
    :return: string
    """
    if args.action == 'backup':
        if args.list:
            stdout = 'DEVNULL'
        elif args.hostname:
            if args.verbose:
                stdout = 'STDOUT'
            else:
                stdout = 'DEVNULL'
        else:
            stdout = 'DEVNULL'
        return stdout
    elif args.action == 'restore':
        if args.verbose:
            stdout = 'STDOUT'
        else:
            stdout = 'DEVNULL'
        return stdout
    else:
        stdout = 'STDOUT'
        return stdout


def map_dict_folder(os_name):
    """
    Mapping folder structure to dictionary
    :param os_name: Name of operating system
    :return: Dictionary folder structure
    """
    # Set an empty dictionary folders
    folders = {}
    # Check operating system
    if os_name == 'Unix':
        folders['User'] = '/home'
        folders['Config'] = '/etc'
        folders['Application'] = '/usr'
        folders['System'] = '/'
        folders['Log'] = '/var/log'
    elif os_name == 'Windows':
        folders['User'] = '/cygdrive/c/Users'
        folders['Config'] = '/cygdrive/c/ProgramData'
        folders['Application'] = "'/cygdrive/c/Program\ Files'"
        folders['System'] = '/cygdrive/c'
        folders['Log'] = '/cygdrive/c/Windows/System32/winevt'
    elif os_name == 'MacOS':
        folders['User'] = '/Users'
        folders['Config'] = '/private/etc'
        folders['Application'] = '/Applications'
        folders['System'] = '/'
        folders['Log'] = '/private/var/log'
    # Return dictionary with folder structure
    return folders


def compose_command(flags, host):
    """
    Compose rsync command for action
    :param flags: Dictionary than contains info for command
    :param host: Hostname of machine
    :return: list
    """
    print_verbose(args.verbose, 'Build a rsync command')
    # Set rsync binary
    if flags.rsync:
        if os.path.exists(flags.rsync):
            command = [flags.rsync]
        else:
            print(utility.PrintColor.YELLOW +
                  'WARNING: rsync binary {0} not exist! Set default.'.format(args.rsync)
                  + utility.PrintColor.END)
            command = ['rsync']
    else:
        command = ['rsync']
    catalog = read_catalog(catalog_path)
    if flags.action == 'backup':
        # Set mode option
        if flags.mode == 'Full':
            command.append('-ah')
            command.append('--no-links')
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Incremental':
            last_bck = get_last_backup(catalog)
            if last_bck:
                command.append('-ahu')
                command.append('--no-links')
                if not flags.sfrom:
                    command.append('--link-dest={0}'.format(last_bck[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Incremental')
            else:
                command.append('-ah')
                command.append('--no-links')
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Differential':
            last_full = get_last_full(catalog)
            if last_full:
                command.append('-ahu')
                command.append('--no-links')
                if not flags.sfrom:
                    command.append('--link-dest={0}'.format(last_full[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Differential')
            else:
                command.append('-ah')
                command.append('--no-links')
                # Write catalog file
                write_catalog(catalog_path, backup_id, 'type', 'Full')
        elif flags.mode == 'Mirror':
            command.append('-ah')
            command.append('--delete')
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'type', 'Mirror')
        # Set verbosity
        if flags.verbose:
            command.append('-vP')
        # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set compress mode
        if flags.compress:
            command.append('-z')
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            utility.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        if flags.log:
            log_path = os.path.join(compose_destination(host, flags.destination), 'backup.log')
            command.append(
                '--log-file={0}'.format(log_path)
            )
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    elif flags.action == 'restore':
        command.append('-ahu --no-perms --no-owner --no-group')
        if flags.verbose:
            command.append('-vP')
            # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set mirror mode
        if flags.mirror:
            command.append('--delete')
            command.append('--ignore-times')
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            utility.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        if flags.log:
            log_path = os.path.join(rpath, 'restore.log')
            command.append(
                '--log-file={0}'.format(log_path)
            )
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    elif flags.action == 'export':
        command.append('-ahu --no-perms --no-owner --no-group')
        if flags.verbose:
            command.append('-vP')
            # Set quite mode
        if flags.skip_err:
            command.append('--quiet')
        # Set I/O timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set mirror mode
        if flags.mirror:
            command.append('--delete')
            command.append('--ignore-times')
        # Set cut mode
        if flags.cut:
            command.append('--remove-source-files')
        # Set includes
        if flags.include:
            for include in flags.include:
                command.append('--include={0}'.format(include))
            command.append('--exclude="*"')
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append('--exclude={0}'.format(exclude))
        # Set timeout
        if flags.timeout:
            command.append('--timeout={0}'.format(flags.timeout))
        # Set bandwidth limit
        if flags.bwlimit:
            command.append('--bwlimit={0}'.format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # No copy symbolic link
        if flags.all:
            command.append('--safe-links')
        # Set dry-run mode
        if flags.dry_run:
            command.append('--dry-run')
            utility.write_log(log_args['status'], log_args['destination'], 'INFO', 'dry-run mode activate')
        if flags.log:
            log_path = os.path.join(flags.catalog, 'export.log')
            command.append(
                '--log-file={0}'.format(log_path)
            )
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'rsync log path: {0}'.format(log_path))
    print_verbose(args.verbose, 'Command flags are: {0}'.format(' '.join(command)))
    return command


def compose_source(action, os_name, sources):
    """
    Compose source
    :param action: command action (backup, restore, archive)
    :param os_name: Name of operating system
    :param sources: Dictionary or string than contains the paths of source
    :return: list
    """
    if action == 'backup':
        src_list = []
        # Add include to the list
        folders = map_dict_folder(os_name)
        # Write catalog file
        write_catalog(catalog_path, backup_id, 'os', os_name)
        custom = True
        if 'System' in sources:
            src_list.append(':{0}'.format(folders['System']))
            return src_list
        if 'User' in sources:
            src_list.append(':{0}'.format(folders['User']))
            custom = False
        if 'Config' in sources:
            src_list.append(':{0}'.format(folders['Config']))
            custom = False
        if 'Application' in sources:
            src_list.append(':{0}'.format(folders['Application']))
            custom = False
        if 'Log' in sources:
            src_list.append(':{0}'.format(folders['Log']))
            custom = False
        if custom:
            # This is custom data
            for custom_data in sources:
                src_list.append(':{0}'.format("'" + custom_data.replace("'", "'\\''") + "'"))
        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'OS {0}; backup folder {1}'.format(os_name, ' '.join(src_list)))
        print_verbose(args.verbose, 'Include this criteria: {0}'.format(' '.join(src_list)))
        return src_list


def compose_restore_src_dst(backup_os, restore_os, restore_path):
    """
    Compare dictionary of folder backup and restore
    :param backup_os: backup structure folders
    :param restore_os: restore structure folders
    :param restore_path: path of backup
    :return: set
    """
    # Compare folder of the backup os and restore os
    b_folders = map_dict_folder(backup_os)
    r_folders = map_dict_folder(restore_os)
    for key in b_folders.keys():
        if restore_path in b_folders[key]:
            rsrc = os.path.join(restore_path, '*')
            rdst = r_folders[key]
            if rsrc and rdst:
                return rsrc, rdst
        else:
            rsrc = restore_path
            rdst = os.path.join(r_folders['System'], 'restore_{0}'.format(utility.time_for_folder()))
            if rsrc and rdst:
                return rsrc, rdst


def get_restore_os():
    """
    Get the operating system value on catalog by id
    :return: os value (string)
    """
    config = read_catalog(os.path.join(args.catalog, '.catalog.cfg'))
    return config.get(args.id, 'os')


def compose_destination(computer_name, folder):
    """
    Compose folder destination of backup
    :param computer_name: name of source computer
    :param folder: path of backup
    :return: string
    """
    # Create root folder of backup
    first_layer = os.path.join(folder, computer_name)
    # Check if backup is a Mirror or not
    if args.mode != 'Mirror':
        second_layer = os.path.join(first_layer, utility.time_for_folder())
    else:
        second_layer = os.path.join(first_layer, 'mirror_backup')
    if not os.path.exists(first_layer):
        os.mkdir(first_layer)
        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Create folder {0}'.format(first_layer))
    if not os.path.exists(second_layer):
        os.mkdir(second_layer)
        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Create folder {0}'.format(second_layer))
    # Write catalog file
    write_catalog(catalog_path, backup_id, 'path', second_layer)
    print_verbose(args.verbose, 'Destination is {0}'.format(second_layer))
    return second_layer


def get_last_full(catalog):
    """
    Get the last full
    :param catalog: configparser object
    :return: path (string), os (string)
    """
    config = catalog
    if config:
        dates = []
        for bid in config.sections():
            if config.get(bid, 'type') == 'Full' \
                    and config.get(bid, 'name') == hostname \
                    and (not config.has_option(bid, 'cleaned') or not config.has_option(bid, 'archived')):
                try:
                    dates.append(utility.string_to_time(config.get(bid, 'timestamp')))
                except configparser.NoOptionError:
                    print(utility.PrintColor.RED +
                          "ERROR: Corrupted catalog! No found timestamp in {0}".format(bid) + utility.PrintColor.END)
                    exit(2)
        if dates:
            last_full = utility.time_to_string(max(dates))
            if last_full:
                print_verbose(args.verbose, 'Last full is {0}'.format(last_full))
                for bid in config.sections():
                    if config.get(bid, 'type') == 'Full' and \
                            config.get(bid, 'name') == hostname and \
                            config.get(bid, 'timestamp') == last_full:
                        return config.get(bid, 'path'), config.get(bid, 'os')
    else:
        return False


def get_last_backup(catalog):
    """
    Get the last available backup
    :param catalog: configparser object
    :return: path (string), os (string)
    """
    config = catalog
    dates = []
    if config:
        for bid in config.sections():
            if config.get(bid, 'name') == hostname \
                    and (not config.has_option(bid, 'cleaned') or not config.has_option(bid, 'archived')):
                try:
                    dates.append(utility.string_to_time(config.get(bid, 'timestamp')))
                except configparser.NoOptionError:
                    print(utility.PrintColor.RED +
                          "ERROR: Corrupted catalog! No found timestamp in {0}".format(bid) + utility.PrintColor.END)
                    exit(2)
        if dates:
            dates.sort()
            last = utility.time_to_string(dates[-1])
            if last:
                for bid in config.sections():
                    if config.get(bid, 'name') == hostname and config.get(bid, 'timestamp') == last:
                        return config.get(bid, 'path'), config.get(bid, 'os')
    else:
        return False


def count_full(config, name):
    """
    Count all full (and Incremental) backup in a catalog
    :param config: configparser object
    :param name: hostname of machine
    :return: count (int)
    """
    count = 0
    if config:
        for bid in config.sections():
            if ((config.get(bid, 'type') == 'Full' or
                 config.get(bid, 'type') == 'Incremental') and
                    config.get(bid, 'name') == name):
                count += 1
    return count


def list_backup(config, name):
    """
    Count all full in a catalog
    :param config: configparser object
    :param name: hostname of machine
    :return: r_list (list)
    """
    r_list = list()
    if config:
        for bid in config.sections():
            if config.get(bid, 'name') == name:
                r_list.append(bid)
    return r_list


def read_catalog(catalog):
    """
    Read a catalog file
    :param catalog: catalog file
    :return: catalog file (configparser)
    """
    config = configparser.ConfigParser()
    file = config.read(catalog)
    if file:
        return config
    else:
        print_verbose(args.verbose, 'Catalog not found! Create a new one.')
        if os.path.exists(os.path.dirname(catalog)):
            utility.touch(catalog)
            config.read(catalog)
            return config
        else:
            print(utility.PrintColor.RED +
                  'ERROR: Folder {0} not exist!'.format(os.path.dirname(catalog)) + utility.PrintColor.END)
            exit(1)


def write_catalog(catalog, section, key, value):
    """
    Write catalog file
    :param catalog: path catalog file
    :param section: section of catalog file
    :param key: key of catalog file
    :param value: value of key of catalog file
    :return:
    """
    config = read_catalog(catalog)
    if not args.dry_run:
        # Add new section
        try:
            config.add_section(section)
            config.set(section, key, value)
        except configparser.DuplicateSectionError:
            config.set(section, key, value)
        # Write new section
        with open(catalog, 'w') as configfile:
            config.write(configfile)


def retention_policy(host, catalog, logpath):
    """
    Retention policy
    :param host: hostname of machine
    :param catalog: catalog file
    :param logpath: path of log file
    """
    config = read_catalog(catalog)
    full_count = count_full(config, host)
    if len(args.retention) >= 3:
        print(utility.PrintColor.RED + 'ERROR: The "--retention or -r" parameter must have two integers. '
                                       'Three or more arguments specified: {}'.format(args.retention) +
              utility.PrintColor.END)
        return
    if args.retention[1]:
        backup_list = list_backup(config, host)[-args.retention[1]:]
    else:
        backup_list = list()
    cleanup = -1
    for bid in config.sections():
        if bid not in backup_list:
            if (config.get(bid, 'cleaned', fallback='unset') == 'unset') and (config.get(bid, 'name') == host):
                type_backup = config.get(bid, 'type')
                path = config.get(bid, 'path')
                date = config.get(bid, 'timestamp')
                if (type_backup == 'Full' or type_backup == 'Incremental') and (full_count <= 1):
                    continue
                utility.print_verbose(args.verbose, "Check cleanup this backup {0}. Folder {1}".format(bid, path))
                if not dry_run("Cleanup {0} backup folder".format(path)):
                    cleanup = utility.cleanup(path, date, args.retention[0])
                if not os.path.exists(path):
                    utility.print_verbose(args.verbose, "This folder {0} does not exist. "
                                                        "The backup has already been cleaned.".format(path))
                    cleanup = 0
                if cleanup == 0:
                    write_catalog(catalog, bid, 'cleaned', 'True')
                    print(utility.PrintColor.GREEN + 'SUCCESS: Cleanup {0} successfully.'.format(path) +
                          utility.PrintColor.END)
                    utility.write_log(log_args['status'], logpath, 'INFO',
                                      'Cleanup {0} successfully.'.format(path))
                elif cleanup == 1:
                    print(utility.PrintColor.RED + 'ERROR: Cleanup {0} failed.'.format(path) +
                          utility.PrintColor.END)
                    utility.write_log(log_args['status'], logpath, 'ERROR',
                                      'Cleanup {0} failed.'.format(path))
                else:
                    utility.print_verbose(args.verbose, "No cleanup backup {0}. Folder {1}".format(bid, path))


def archive_policy(catalog, destination):
    """
    Archive policy
    :param catalog: catalog file
    :param destination: destination pth of archive file
    """
    config = read_catalog(catalog)
    archive = -1
    for bid in config.sections():
        full_count = count_full(config, config.get(bid, 'name'))
        if (config.get(bid, 'archived', fallback='unset') == 'unset') and not \
                (config.get(bid, 'cleaned', fallback=False)):
            type_backup = config.get(bid, 'type')
            path = config.get(bid, 'path')
            date = config.get(bid, 'timestamp')
            logpath = os.path.join(os.path.dirname(path), 'general.log')
            utility.print_verbose(args.verbose, "Check archive this backup {0}. Folder {1}".format(bid, path))
            if (type_backup == 'Full') and (full_count <= 1):
                continue
            if not dry_run("Archive {0} backup folder".format(path)):
                archive = utility.archive(path, date, args.days, destination)
            if archive == 0:
                write_catalog(catalog, bid, 'archived', 'True')
                print(utility.PrintColor.GREEN + 'SUCCESS: Archive {0} successfully.'.format(path) +
                      utility.PrintColor.END)
                utility.write_log(log_args['status'], logpath, 'INFO',
                                  'Archive {0} successfully.'.format(path))
            elif archive == 1:
                print(utility.PrintColor.RED + 'ERROR: Archive {0} failed.'.format(path) +
                      utility.PrintColor.END)
                utility.write_log(log_args['status'], logpath, 'ERROR',
                                  'Archive {0} failed.'.format(path))
            else:
                utility.print_verbose(args.verbose, "No archive backup {0}. Folder {1}".format(bid, path))


def deploy_configuration(computer, user):
    """
    Deploy configuration on remote machine (run "ssh-copy-id -i pub_file -f <user>@<computer>")
    :param computer: remote computer than deploy RSA key
    :param user: remote user on computer
    """
    # Create home path
    home = os.path.expanduser('~')
    ssh_folder = os.path.join(home, '.ssh')
    # Remove private key file
    id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
    print_verbose(args.verbose, 'Public id_rsa is {0}'.format(id_rsa_pub_file))
    if not dry_run('Copying configuration to {0}'.format(computer)):
        if os.path.exists(id_rsa_pub_file):
            print('Copying configuration to' + utility.PrintColor.BOLD + ' {0}'.format(computer) +
                  utility.PrintColor.END + '; write the password:')
            return_code = subprocess.call('ssh-copy-id -i {0} {1}@{2}'.format(id_rsa_pub_file, user, computer),
                                          shell=True)
            print_verbose(args.verbose, 'Return code of ssh-copy-id: {0}'.format(return_code))
            if return_code == 0:
                print(utility.PrintColor.GREEN + "SUCCESS: Configuration copied successfully on {0}!".format(computer) +
                      utility.PrintColor.END)
            else:
                print(utility.PrintColor.RED + "ERROR: Configuration has not been copied successfully on {0}!".format(
                    computer) +
                      utility.PrintColor.END)
        else:
            print(utility.PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub is not exist" +
                  utility.PrintColor.END)
            exit(2)


def remove_configuration():
    """
    Remove a new configuration (remove an exist RSA key pair)
    """
    # Create home path
    home = os.path.expanduser('~')
    ssh_folder = os.path.join(home, '.ssh')
    if not dry_run('Remove private id_rsa'):
        if utility.confirm('Are you sure to remove existing rsa keys?'):
            # Remove private key file
            id_rsa_file = os.path.join(ssh_folder, 'id_rsa')
            print_verbose(args.verbose, 'Remove private id_rsa {0}'.format(id_rsa_file))
            if os.path.exists(id_rsa_file):
                os.remove(id_rsa_file)
            else:
                print(
                    utility.PrintColor.YELLOW + "WARNING: Private key ~/.ssh/id_rsa is not exist" +
                    utility.PrintColor.END)
                exit(2)
            # Remove public key file
            id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
            print_verbose(args.verbose, 'Remove public id_rsa {0}'.format(id_rsa_pub_file))
            if os.path.exists(id_rsa_pub_file):
                os.remove(id_rsa_pub_file)
            else:
                print(
                    utility.PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub is not exist" +
                    utility.PrintColor.END)
                exit(2)
            print(utility.PrintColor.GREEN + "SUCCESS: Removed configuration successfully!" + utility.PrintColor.END)


def new_configuration():
    """
    Create a new configuration (create a RSA key pair)
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend

    if not dry_run('Generate private/public key pair'):
        # Generate private/public key pair
        print_verbose(args.verbose, 'Generate private/public key pair')
        private_key = rsa.generate_private_key(backend=default_backend(), public_exponent=65537,
                                               key_size=2048)
        # Get public key in OpenSSH format
        print_verbose(args.verbose, 'Get public key in OpenSSH format')
        public_key = private_key.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                                           serialization.PublicFormat.OpenSSH)
        # Get private key in PEM container format
        print_verbose(args.verbose, 'Get private key in PEM container format')
        pem = private_key.private_bytes(encoding=serialization.Encoding.PEM,
                                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                                        encryption_algorithm=serialization.NoEncryption())
        # Decode to printable strings
        private_key_str = pem.decode('utf-8')
        public_key_str = public_key.decode('utf-8')
        # Create home path
        home = os.path.expanduser('~')
        # Create folder .ssh
        ssh_folder = os.path.join(home, '.ssh')
        print_verbose(args.verbose, 'Create folder {0}'.format(ssh_folder))
        if not os.path.exists(ssh_folder):
            os.mkdir(ssh_folder, mode=0o755)
        # Create private key file
        id_rsa_file = os.path.join(ssh_folder, 'id_rsa')
        print_verbose(args.verbose, 'Create private key file {0}'.format(id_rsa_file))
        if not os.path.exists(id_rsa_file):
            with open(id_rsa_file, 'w') as id_rsa:
                os.chmod(id_rsa_file, mode=0o600)
                id_rsa.write(private_key_str)
        else:
            print(utility.PrintColor.YELLOW + "WARNING: Private key ~/.ssh/id_rsa exists" + utility.PrintColor.END)
            print('If you want to use the existing key, run "bb config --deploy name_of_machine", '
                  'otherwise to remove it, '
                  'run "bb config --remove"')
            exit(2)
        # Create private key file
        id_rsa_pub_file = os.path.join(ssh_folder, 'id_rsa.pub')
        print_verbose(args.verbose, 'Create public key file {0}'.format(id_rsa_pub_file))
        if not os.path.exists(id_rsa_pub_file):
            with open(id_rsa_pub_file, 'w') as id_rsa_pub:
                os.chmod(id_rsa_pub_file, mode=0o644)
                id_rsa_pub.write(public_key_str)
        else:
            print(utility.PrintColor.YELLOW + "WARNING: Public key ~/.ssh/id_rsa.pub exists" + utility.PrintColor.END)
            print('If you want to use the existing key, run "bb config --deploy name_of_machine", '
                  'otherwise to remove it, '
                  'run "bb config --remove"')
            exit(2)
        print(utility.PrintColor.GREEN + "SUCCESS: New configuration successfully created!" + utility.PrintColor.END)


def check_configuration(ip):
    """
    Check if configuration is correctly deployed
    :param ip: hostname of pc or ip address
    :return: output of command
    """
    from subprocess import check_output
    try:
        out = check_output(["ssh-keyscan", "{0}".format(ip)])
        if not out:
            return False
    except subprocess.CalledProcessError:
        return False


def init_catalog(catalog):
    """
    :param catalog: catalog file
    """
    config = read_catalog(catalog)
    for cid in config.sections():
        if not os.path.exists(config[cid]['path']):
            print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
            config.remove_section(cid)
    # Write file
    with open(catalog, 'w') as configfile:
        config.write(configfile)


def delete_host(catalog, host):
    """
    :param catalog: catalog file
    :param host: hostname or ip address
    """
    config = read_catalog(catalog)
    for cid in config.sections():
        if config.get(cid, "name") == host:
            if not os.path.exists(config[cid]['path']):
                print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                config.remove_section(cid)
            else:
                path = config.get(cid, 'path')
                date = config.get(cid, 'timestamp')
                cleanup = utility.cleanup(path, date, 0)
                if cleanup == 0:
                    print(utility.PrintColor.GREEN + 'SUCCESS: Delete {0} successfully.'.format(path) +
                          utility.PrintColor.END)
                    print_verbose(args.verbose, "Backup-id {0} has been removed to catalog!".format(cid))
                    config.remove_section(cid)
                elif cleanup == 1:
                    print(utility.PrintColor.RED + 'ERROR: Delete {0} failed.'.format(path) +
                          utility.PrintColor.END)
    # Write file
    with open(catalog, 'w') as configfile:
        config.write(configfile)


def clean_catalog(catalog):
    """
    :param catalog: catalog file
    """
    config = read_catalog(catalog)
    print_verbose(args.verbose, "Start check catalog file: {0}!".format(catalog))
    for cid in config.sections():
        print_verbose(args.verbose, "Check backup-id: {0}!".format(cid))
        mod = False
        if not config.get(cid, 'type', fallback=''):
            config.set(cid, 'type', 'Incremental')
            mod = True
        if not config.get(cid, 'path', fallback=''):
            config.remove_section(cid)
            mod = True
        if not config.get(cid, 'name', fallback=''):
            config.set(cid, 'name', 'default')
            mod = True
        if not config.get(cid, 'os', fallback=''):
            config.set(cid, 'os', 'Unix')
            mod = True
        if not config.get(cid, 'timestamp', fallback=''):
            config.set(cid, 'timestamp', utility.time_for_log())
            mod = True
        if not config.get(cid, 'start', fallback=''):
            config.set(cid, 'start', utility.time_for_log())
            mod = True
        if not config.get(cid, 'end', fallback=''):
            config.set(cid, 'end', utility.time_for_log())
            mod = True
        if not config.get(cid, 'status', fallback=''):
            config.set(cid, 'status', '0')
            mod = True
        if mod:
            print(utility.PrintColor.YELLOW +
                  'WARNING: The backup-id {0} has been set to default value, because he was corrupt. '
                  'Check it!'.format(cid) + utility.PrintColor.END)
    # Write file
    with open(catalog, 'w') as configfile:
        config.write(configfile)


def parse_arguments():
    """
    Function get arguments than specified in command line
    :return: parser
    """
    # Create a common parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument('--verbose', '-v', help='Enable verbosity', dest='verbose', action='store_true')
    parent_parser.add_argument('--log', '-l', help='Create a log', dest='log', action='store_true')
    parent_parser.add_argument('--dry-run', '-N', help='Dry run mode', dest='dry_run', action='store_true')

    # Create principal parser
    parser_object = argparse.ArgumentParser(prog='bb', description=utility.PrintColor.BOLD + 'Butterfly Backup'
                                            + utility.PrintColor.END, epilog=check_rsync(),
                                            parents=[parent_parser])
    # Create sub_parser "action"
    action = parser_object.add_subparsers(title='action', description='Valid action', help='Available actions',
                                          dest='action')
    # config session
    config = action.add_parser('config', help='Configuration options', parents=[parent_parser])
    group_config = config.add_argument_group(title='Init configuration')
    group_config_mutually = group_config.add_mutually_exclusive_group()
    group_config_mutually.add_argument('--new', '-n', help='Generate new configuration', dest='new_conf',
                                       action='store_true')
    group_config_mutually.add_argument('--remove', '-r', help='Remove exist configuration', dest='remove_conf',
                                       action='store_true')
    group_config_mutually.add_argument('--init', '-i', help='Reset catalog file. Specify path of backup folder.',
                                       dest='init', action='store')
    group_config_mutually.add_argument('--delete-host', '-D', help='Delete all entry for a single HOST in catalog.',
                                       nargs=2, dest='delete', metavar=('CATALOG', 'HOST'), action='store')
    group_config_mutually.add_argument('--clean', '-c', help='Cleans the catalog if it is corrupt, '
                                                             'setting default values.',
                                       dest='clean', metavar='CATALOG', action='store')
    group_deploy = config.add_argument_group(title='Deploy configuration')
    group_deploy_mutually = group_deploy.add_mutually_exclusive_group()
    group_deploy_mutually.add_argument('--deploy', '-d', help='Deploy configuration to client: hostname or ip address',
                                       dest='deploy_host', action='store')
    group_deploy.add_argument('--user', '-u', help='User of the remote machine',
                              dest='deploy_user', action='store', default=os.getlogin())
    # backup session
    backup = action.add_parser('backup', help='Backup options', parents=[parent_parser])
    group_backup = backup.add_argument_group(title='Backup options')
    single_or_list_group = group_backup.add_mutually_exclusive_group(required=True)
    single_or_list_group.add_argument('--computer', '-c', help='Hostname or ip address to backup', dest='hostname',
                                      action='store')
    single_or_list_group.add_argument('--list', '-L', help='File list of computers or ip addresses to backup',
                                      dest='list', action='store')
    group_backup.add_argument('--destination', '-d', help='Destination path', dest='destination', action='store',
                              required=True)
    group_backup.add_argument('--mode', '-m', help='Backup mode', dest='mode', action='store',
                              choices=['Full', 'Incremental', 'Differential', 'Mirror'], default='Incremental')
    data_or_custom = group_backup.add_mutually_exclusive_group(required=True)
    data_or_custom.add_argument('--data', '-D', help='Data of which you want to backup', dest='data', action='store',
                                choices=['User', 'Config', 'Application', 'System', 'Log'], nargs='+')
    data_or_custom.add_argument('--custom-data', '-C', help='Custom path of which you want to backup',
                                dest='customdata', action='store', nargs='+')
    group_backup.add_argument('--user', '-u', help='Login name used to log into the remote host (being backed up)',
                              dest='user', action='store', default=os.getlogin())
    group_backup.add_argument('--type', '-t', help='Type of operating system to backup', dest='type', action='store',
                              choices=['Unix', 'Windows', 'MacOS'], required=True)
    group_backup.add_argument('--compress', '-z', help='Compress data', dest='compress',
                              action='store_true')
    group_backup.add_argument('--retention', '-r', help='First argument are days of backup retention. '
                                                        'Second argument is minimum number of backup retention',
                              dest='retention', action='store', nargs='*', metavar=('DAYS', 'NUMBER'), type=int)
    group_backup.add_argument('--parallel', '-p', help='Number of parallel jobs', dest='parallel', action='store',
                              type=int, default=5)
    group_backup.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                              type=int)
    group_backup.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_backup.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_backup.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                              type=int)
    group_backup.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    group_backup.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store', nargs='+')
    group_backup.add_argument('--start-from', '-s', help='Backup id where start a new backup', dest='sfrom',
                              action='store', metavar='ID')
    # restore session
    restore = action.add_parser('restore', help='Restore options', parents=[parent_parser])
    group_restore = restore.add_argument_group(title='Restore options')
    group_restore.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                               required=True)
    restore_id_or_last = group_restore.add_mutually_exclusive_group(required=True)
    restore_id_or_last.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    restore_id_or_last.add_argument('--last', '-L', help='Last available backup', dest='last', action='store_true')
    group_restore.add_argument('--user', '-u', help="Login name used to log into the remote host "
                                                    "(where you're restoring)", dest='user',
                               action='store', default=os.getlogin())
    group_restore.add_argument('--computer', '-c', help='Hostname or ip address to perform restore', dest='hostname',
                               action='store', required=True)
    group_restore.add_argument('--type', '-t', help='Type of operating system to perform restore', dest='type',
                               action='store', choices=['Unix', 'Windows', 'MacOS'])
    group_restore.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                               type=int)
    group_restore.add_argument('--mirror', '-m', help='Mirror mode', dest='mirror', action='store_true')
    group_restore.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_restore.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_restore.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                               type=int)
    group_restore.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    group_restore.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store', nargs='+')
    # archive session
    archive = action.add_parser('archive', help='Archive options', parents=[parent_parser])
    group_archive = archive.add_argument_group(title='Archive options')
    group_archive.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                               required=True)
    group_archive.add_argument('--days', '-D', help='Number of days of archive retention', dest='days',
                               action='store', type=int, default=30)
    group_archive.add_argument('--destination', '-d', help='Archive destination path', dest='destination',
                               action='store', required=True)
    # list session
    list_action = action.add_parser('list', help='List options', parents=[parent_parser])
    group_list = list_action.add_argument_group(title='List options')
    group_list.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                            required=True)
    group_list_mutually = group_list.add_mutually_exclusive_group()
    group_list_mutually.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    group_list_mutually.add_argument('--archived', '-a', help='List only archived backup', dest='archived',
                                     action='store_true')
    group_list_mutually.add_argument('--cleaned', '-c', help='List only cleaned backup', dest='cleaned',
                                     action='store_true')
    group_list_mutually.add_argument('--computer', '-H', help='List only match hostname or ip', dest='hostname',
                                     action='store')
    group_list_mutually.add_argument('--detail', '-d', help='List detail of file and folder of specific backup-id',
                                     dest='detail', action='store', metavar='ID')
    group_list.add_argument('--oneline', '-o', help='One line output', dest='oneline', action='store_true')
    # export session
    export_action = action.add_parser('export', help='Export options', parents=[parent_parser])
    group_export = export_action.add_argument_group(title='Export options')
    group_export.add_argument('--catalog', '-C', help='Folder where is catalog file', dest='catalog', action='store',
                              required=True)
    group_export_id_or_all = group_export.add_mutually_exclusive_group()
    group_export_id_or_all.add_argument('--backup-id', '-i', help='Backup-id of backup', dest='id', action='store')
    group_export_id_or_all.add_argument('--all', '-A', help='All backup', dest='all', action='store_true')
    group_export.add_argument('--destination', '-d', help='Destination path', dest='destination', action='store',
                              required=True)
    group_export.add_argument('--mirror', '-m', help='Mirror mode', dest='mirror', action='store_true')
    group_export.add_argument('--cut', '-c', help='Cut mode. Delete source', dest='cut', action='store_true')
    group_export_mutually = group_export.add_mutually_exclusive_group()
    group_export_mutually.add_argument('--include', '-I', help='Include pattern', dest='include', action='store',
                                       nargs='+')
    group_export_mutually.add_argument('--exclude', '-E', help='Exclude pattern', dest='exclude', action='store',
                                       nargs='+')
    group_export.add_argument('--timeout', '-T', help='I/O timeout in seconds', dest='timeout', action='store',
                              type=int)
    group_export.add_argument('--skip-error', '-e', help='Skip error', dest='skip_err', action='store_true')
    group_export.add_argument('--rsync-path', '-R', help='Custom rsync path', dest='rsync', action='store')
    group_export.add_argument('--bwlimit', '-b', help='Bandwidth limit in KBPS.', dest='bwlimit', action='store',
                              type=int)
    group_export.add_argument('--ssh-port', '-P', help='Custom ssh port.', dest='port', action='store', type=int)
    # Return all args
    parser_object.add_argument('--version', '-V', help='Print version', dest='version', action='store_true')
    return parser_object


if __name__ == '__main__':
    parser = parse_arguments()
    args = parser.parse_args()

    # Check version flag
    if args.version:
        print_version(VERSION)

    # Check action
    if not args.action:
        parser.print_help()

    # Check config session
    if args.action == 'config':
        if args.new_conf:
            new_configuration()
        elif args.remove_conf:
            remove_configuration()
        elif args.deploy_host:
            deploy_configuration(args.deploy_host, args.deploy_user)
        elif args.init:
            catalog_path = os.path.join(args.init, '.catalog.cfg')
            init_catalog(catalog_path)
        elif args.delete:
            catalog_path = os.path.join(args.delete[0], '.catalog.cfg')
            delete_host(catalog_path, args.delete[1])
        elif args.clean:
            catalog_path = os.path.join(args.clean, '.catalog.cfg')
            clean_catalog(catalog_path)
        else:
            parser.print_usage()
            print('For ' + utility.PrintColor.BOLD + 'config' + utility.PrintColor.END + ' usage, "--help" or "-h"')
            exit(1)

    # Check backup session
    if args.action == 'backup':
        hostnames = []
        cmds = []
        logs = []
        if args.hostname:
            # Computer list
            hostnames.append(args.hostname)
        elif args.list:
            if os.path.exists(args.list):
                list_file = open(args.list, 'r').read().split()
                for line in list_file:
                    # Computer list
                    hostnames.append(line)
            else:
                print(utility.PrintColor.RED + 'ERROR: The file {0} not exist!'.format(args.list)
                      + utility.PrintColor.END)
        else:
            parser.print_usage()
            print('For ' + utility.PrintColor.BOLD + 'backup' + utility.PrintColor.END + ' usage, "--help" or "-h"')
            exit(1)
        for hostname in hostnames:
            if not utility.check_ssh(hostname):
                print(utility.PrintColor.RED + 'ERROR: The port 22 on {0} is closed!'.format(hostname)
                      + utility.PrintColor.END)
                continue
            if not args.verbose:
                if check_configuration(hostname):
                    print(utility.PrintColor.RED + '''ERROR: For bulk or silently backup, deploy configuration!
                            See bb deploy --help or specify --verbose''' + utility.PrintColor.END)
                    continue
            # Log information's
            backup_id = '{}'.format(utility.new_id())
            log_args = {
                'id': backup_id,
                'hostname': hostname,
                'status': args.log,
                'destination': os.path.join(args.destination, hostname, 'general.log')
            }
            logs.append(log_args)
            catalog_path = os.path.join(args.destination, '.catalog.cfg')
            backup_catalog = read_catalog(catalog_path)
            # Compose command
            cmd = compose_command(args, hostname)
            # Check if start-from is specified
            if args.sfrom:
                if backup_catalog.has_section(args.sfrom):
                    # Check if exist path of backup
                    if os.path.exists(backup_catalog[args.sfrom]['path']):
                        cmd.append('--copy-dest={0}'.format(backup_catalog[args.sfrom]['path']))
                    else:
                        print(utility.PrintColor.YELLOW +
                              'WARNING: Backup folder {0} not exist!'.format(backup_catalog[args.sfrom]['path'])
                              + utility.PrintColor.END)
                else:
                    print(utility.PrintColor.RED +
                          'ERROR: Backup id {0} not exist in catalog {1}!'.format(args.sfrom, args.destination)
                          + utility.PrintColor.END)
                    exit(1)
            print_verbose(args.verbose, 'Create a folder structure for {0} os'.format(args.type))
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'name', hostname)
            # Compose source
            if args.data:
                srcs = args.data
                source_list = compose_source(args.action, args.type, srcs)
            elif args.customdata:
                srcs = args.customdata
                source_list = compose_source(args.action, args.type, srcs)
            else:
                source_list = []
            # Check if hostname is localhost or 127.0.0.1
            if (hostname == "localhost") or (hostname == "LOCALHOST") or (hostname == "127.0.0.1"):
                # Compose source with only path of folder list
                cmd.append(" ".join(source_list)[1:])
            else:
                # Compose source <user>@<hostname> format
                cmd.append('{0}@{1}'.format(args.user, hostname).__add__(" ".join(source_list)))
            # Compose destination
            bck_dst = compose_destination(hostname, args.destination)
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'Backup on folder {0}'.format(bck_dst))
            cmd.append(bck_dst)
            # Compose pull commands
            cmds.append(' '.join(cmd))
            # Write catalog file
            write_catalog(catalog_path, backup_id, 'timestamp', utility.time_for_log())
            # Create a symlink for last backup
            utility.make_symlink(bck_dst, os.path.join(args.destination, hostname, 'last_backup'))
        # Start backup
        run_in_parallel(start_process, cmds, args.parallel)

    # Check restore session
    if args.action == 'restore':
        cmds = []
        logs = []
        rhost = ''
        hostname = args.hostname
        rpath = ''
        bos = ''
        ros = ''
        rfolders = ''
        if not args.type and args.id:
            args.type = get_restore_os()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, '.catalog.cfg')
        restore_catalog = read_catalog(catalog_path)
        # Check if select backup-id or last backup
        if args.last:
            rhost = hostname
            last_backup = get_last_backup(restore_catalog)
            if not args.type:
                args.type = last_backup[1]
            rpath = last_backup[0]
            if os.path.exists(rpath):
                bos = last_backup[1]
                ros = args.type
                rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
            else:
                print(utility.PrintColor.RED + 'ERROR: Backup folder {0} not exist!'.format(rpath) +
                      utility.PrintColor.END)
                exit(1)
        elif args.id:
            # Check catalog backup id
            if restore_catalog.has_section(args.id):
                # Check if exist path of backup
                if os.path.exists(restore_catalog[args.id]['path']):
                    rhost = hostname
                    rpath = restore_catalog[args.id]['path']
                    bos = restore_catalog[args.id]['os']
                    ros = args.type
                    rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
                else:
                    print(utility.PrintColor.RED +
                          'ERROR: Backup folder {0} not exist!'.format(restore_catalog[args.id]['path'])
                          + utility.PrintColor.END)
                    exit(1)
            else:
                print(utility.PrintColor.RED +
                      'ERROR: Backup id {0} not exist in catalog {1}!'.format(args.id, args.catalog)
                      + utility.PrintColor.END)
                exit(1)
        # Test connection
        if not utility.check_ssh(rhost):
            print(utility.PrintColor.RED + 'ERROR: The port 22 on {0} is closed!'.format(rhost)
                  + utility.PrintColor.END)
            exit(1)
        if not args.verbose:
            if not check_configuration(rhost):
                print(utility.PrintColor.RED + '''ERROR: For bulk or silently backup to deploy configuration!
                                            See bb deploy --help or specify --verbose''' + utility.PrintColor.END)
                exit(1)
        log_args = {
            'hostname': rhost,
            'status': args.log,
            'destination': os.path.join(os.path.dirname(rpath), 'general.log')
        }
        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                          'Restore on {0}'.format(rhost))
        for rf in rfolders:
            # Append logs
            logs.append(log_args)
            # Compose command
            cmd = compose_command(args, rhost)
            # ATTENTION: permit access to anyone users
            if ros == 'Windows':
                cmd.append('--chmod=ugo=rwX')
            # Compose source and destination
            src_dst = compose_restore_src_dst(bos, ros, os.path.basename(rf))
            if src_dst:
                src = src_dst[0]
                # Compose source
                cmd.append(os.path.join(rpath, src))
                dst = src_dst[1]
                if (hostname == "localhost") or (hostname == "LOCALHOST") or (hostname == "127.0.0.1"):
                    # Compose destination only with path of folder
                    cmd.append('{}'.format(dst))
                else:
                    # Compose destination <user>@<hostname> format
                    cmd.append('{0}@{1}:'.format(args.user, rhost).__add__(dst))
                # Add command
                if utility.confirm("Want to do restore path {0}?".format(os.path.join(rpath, src))):
                    cmds.append(' '.join(cmd))
        # Start restore
        run_in_parallel(start_process, cmds, 1)

    # Check archive session
    if args.action == 'archive':
        # Log info
        log_args = {
            'status': args.log,
            'destination': os.path.join(args.catalog, 'archive.log')
        }
        # Read catalog file
        archive_catalog = os.path.join(args.catalog, '.catalog.cfg')
        # Archive paths
        archive_policy(archive_catalog, args.destination)

    # Check list session
    if args.action == 'list':
        # Log info
        log_args = {
            'status': args.log,
            'destination': os.path.join(args.catalog, 'backup.list')
        }
        # Read catalog file
        list_catalog = read_catalog(os.path.join(args.catalog, '.catalog.cfg'))
        # Check specified argument backup-id
        if args.id:
            if not args.oneline:
                utility.print_verbose(args.verbose, "Select backup-id: {0}".format(args.id))
                if not list_catalog.has_section(args.id):
                    print(utility.PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + utility.PrintColor.END)
                    exit(1)
                print('Backup id: ' + utility.PrintColor.BOLD + args.id +
                      utility.PrintColor.END)
                print('Hostname or ip: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['name'] +
                      utility.PrintColor.END)
                print('Type: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['type'] +
                      utility.PrintColor.END)
                print('Timestamp: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['timestamp'] +
                      utility.PrintColor.END)
                print('Start: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['start'] +
                      utility.PrintColor.END)
                print('Finish: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['end'] +
                      utility.PrintColor.END)
                print('OS: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['os'] +
                      utility.PrintColor.END)
                print('ExitCode: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['status'] +
                      utility.PrintColor.END)
                print('Path: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['path'] +
                      utility.PrintColor.END)
                if list_catalog.get(args.id, 'cleaned', fallback=False):
                    print('Cleaned: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['cleaned'] +
                          utility.PrintColor.END)
                elif list_catalog.get(args.id, 'archived', fallback=False):
                    print('Archived: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['archived'] +
                          utility.PrintColor.END)
                else:
                    print('List: ' + utility.PrintColor.DARKCYAN + '\n'.join(os.listdir(list_catalog[args.id]['path']))
                          + utility.PrintColor.END)
            else:
                if not list_catalog.has_section(args.id):
                    print(utility.PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + utility.PrintColor.END)
                    exit(1)
                print('Id: ' + utility.PrintColor.BOLD + args.id +
                      utility.PrintColor.END, end=' - ')
                print('Name: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['name'] +
                      utility.PrintColor.END, end=' - ')
                print('Type: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['type'] +
                      utility.PrintColor.END, end=' - ')
                print('Timestamp: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['timestamp'] +
                      utility.PrintColor.END, end=' - ')
                print('Start: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['start'] +
                      utility.PrintColor.END, end=' - ')
                print('Finish: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['end'] +
                      utility.PrintColor.END, end=' - ')
                print('OS: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['os'] +
                      utility.PrintColor.END, end=' - ')
                print('ExitCode: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['status'] +
                      utility.PrintColor.END, end=' - ')
                print('Path: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['path'] +
                      utility.PrintColor.END, end=' - ')
                if list_catalog.get(args.id, 'cleaned', fallback=False):
                    print('Cleaned: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['cleaned'] +
                          utility.PrintColor.END, end=' - ')
                elif list_catalog.get(args.id, 'archived', fallback=False):
                    print('Archived: ' + utility.PrintColor.DARKCYAN + list_catalog[args.id]['archived'] +
                          utility.PrintColor.END, end=' - ')
                else:
                    print('List: ' + utility.PrintColor.DARKCYAN + ' '.join(os.listdir(list_catalog[args.id]['path'])) +
                          utility.PrintColor.END)
        elif args.detail:
            log_args['hostname'] = list_catalog[args.detail]['name']
            logs = [log_args]
            utility.print_verbose(args.verbose, "List detail of backup-id: {0}".format(args.detail))
            print('Detail of backup folder: ' + utility.PrintColor.DARKCYAN
                  + list_catalog[args.detail]['path'] + utility.PrintColor.END)
            print('List: ' + utility.PrintColor.DARKCYAN + '\n'.join(os.listdir(list_catalog[args.detail]['path']))
                  + utility.PrintColor.END)
            if log_args['status']:
                utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                  'BUTTERFLY BACKUP DETAIL (BACKUP-ID: {0} PATH: {1})'.format(
                                      args.detail, list_catalog[args.detail]['path'])
                                  )
                cmd = 'rsync --list-only -r --log-file={0} {1}'.format(log_args['destination'],
                                                                       list_catalog[args.detail]['path'])
            else:
                cmd = 'rsync --list-only -r {0}'.format(list_catalog[args.detail]['path'])
            start_process(cmd)
        elif args.archived:
            utility.print_verbose(args.verbose, "List all archived backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG (ARCHIVED)\n\n'
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG (ARCHIVED)')
            for lid in list_catalog.sections():
                if 'archived' in list_catalog[lid]:
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            utility.pager(text)
        elif args.cleaned:
            utility.print_verbose(args.verbose, "List all cleaned backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG (CLEANED)\n\n'
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG (CLEANED)')
            for lid in list_catalog.sections():
                if 'cleaned' in list_catalog[lid]:
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            utility.pager(text)
        else:
            utility.print_verbose(args.verbose, "List all backup in catalog")
            text = 'BUTTERFLY BACKUP CATALOG\n\n'
            utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                              'BUTTERFLY BACKUP CATALOG')
            if args.hostname:
                for lid in list_catalog.sections():
                    if list_catalog[lid]['name'] == args.hostname:
                        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Backup id: {0}'.format(lid))
                        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                        utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                          'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                        text += 'Backup id: {0}'.format(lid)
                        text += '\n'
                        text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                        text += '\n'
                        text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                        text += '\n\n'
            else:
                for lid in list_catalog.sections():
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Backup id: {0}'.format(lid))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Hostname or ip: {0}'.format(list_catalog[lid]['name']))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Timestamp: {0}'.format(list_catalog[lid]['timestamp']))
                    text += 'Backup id: {0}'.format(lid)
                    text += '\n'
                    text += 'Hostname or ip: {0}'.format(list_catalog[lid]['name'])
                    text += '\n'
                    text += 'Timestamp: {0}'.format(list_catalog[lid]['timestamp'])
                    text += '\n\n'
            utility.pager(text)

    # Check export session
    if args.action == 'export':
        cmds = list()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, '.catalog.cfg')
        export_catalog = read_catalog(catalog_path)
        if os.path.exists(args.destination):
            # Check one export or all
            if args.all:
                # Log info
                log_args = {
                    'hostname': 'all_backup',
                    'status': args.log,
                    'destination': os.path.join(args.destination, 'export.log')
                }
                logs = list()
                logs.append(log_args)
                # Compose command
                print_verbose(args.verbose, 'Build a rsync command')
                cmd = compose_command(args, None)
                # Add source
                cmd.append('{}'.format(os.path.join(args.catalog, '')))
                # Add destination
                cmd.append('{}'.format(args.destination))
            else:
                # Check specified argument backup-id
                if not export_catalog.has_section(args.id):
                    print(utility.PrintColor.RED +
                          'ERROR: Backup-id {0} not exist!'.format(args.id)
                          + utility.PrintColor.END)
                    exit(1)
                # Log info
                log_args = {
                    'hostname': export_catalog[args.id]['Name'],
                    'status': args.log,
                    'destination': os.path.join(args.destination, 'export.log')
                }
                logs = list()
                logs.append(log_args)
                # Compose command
                print_verbose(args.verbose, 'Build a rsync command')
                cmd = compose_command(args, None)
                # Export
                utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                  'Export {0}. Folder {1} to {2}'.format(args.id, export_catalog[args.id]['Path'],
                                                                         args.destination))
                print_verbose(args.verbose, 'Export backup with id {0}'.format(args.id))
                if os.path.exists(export_catalog[args.id]['Path']):
                    # Add source
                    cmd.append('{}'.format(export_catalog[args.id]['Path']))
                    # Add destination
                    cmd.append('{}'.format(os.path.join(args.destination, export_catalog[args.id]['Name'])))
                    utility.write_log(log_args['status'], log_args['destination'], 'INFO',
                                      'Export command {0}.'.format(" ".join(cmd)))
                    # Check cut option
                    if args.cut:
                        write_catalog(os.path.join(args.catalog, '.catalog.cfg'), args.id, 'cleaned', 'True')
            # Start export
            cmds.append(' '.join(cmd))
            run_in_parallel(start_process, cmds, 1)
            if os.path.exists(os.path.join(args.destination, '.catalog.cfg')):
                # Migrate catalog to new file system
                utility.find_replace(os.path.join(args.destination, '.catalog.cfg'), args.catalog.rstrip('/'),
                                     args.destination.rstrip('/'))
        else:
            print(utility.PrintColor.RED +
                  "ERROR: Source or destination path doesn't exist!" + utility.PrintColor.END)
            exit(1)
