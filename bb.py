#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# bb.py -- Butterfly-Backup
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
"""
NAME
    Butterfly Backup - backup/restore/archive tool

DESCRIPTION
    Butterfly Backup is a modern backup program

SYNOPSIS
    bb [ACTION] [OPTIONS]

    bb [-h] [--verbose] [--log] [--dry-run] [--force] [--no-color]
       [--explain-error] [--keytype {rsa,ed25519}] [--version] {config,backup,restore,archive,list,export} ...

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
        $ bb --help
"""

import argparse
import configparser
import getpass
import os
import subprocess
import time
from glob import glob
from multiprocessing import Pool

import utility

# region Global Variables
VERSION = "1.20.0"


# endregion


def check_rsync(rsync_path=None):
    """Check if rsync tool is installed

    :return: string
    """
    if rsync_path:
        if not os.path.exists(rsync_path):
            utility.error(
                "{0} package not found!".format(rsync_path), nocolor=args.color
            )
            exit(1)
    else:
        if not utility.check_tool("rsync"):
            utility.error("rsync package is required!", nocolor=args.color)
            exit(1)


def dry_run(message):
    """Check if dry run mode

    :param message: print message standard output
    :return: boolean
    """
    global args

    if args.dry_run:
        utility.print_verbose(True, message, nocolor=args.color)
        return True
    return False


def run_in_parallel(fn, commands, limit):
    """Run in parallel with limit

    :param fn: function in parallelism
    :param commands: args commands of function
    :param limit: number of parallel process
    """
    global args, catalog_path, logs

    # Start a Pool with "limit" processes
    pool = Pool(processes=limit)
    jobs = []
    necessaries_retries = []

    for command, plog in zip(commands, logs):
        # Run the function
        proc = pool.apply_async(func=fn, args=(command,))
        jobs.append(proc)
        print("info: Start {0} on {1}".format(args.action, plog["hostname"]))
        utility.print_verbose(
            args.verbose, "rsync command: {0}".format(command), nocolor=args.color
        )
        utility.write_log(
            log_args["status"],
            plog["destination"],
            "INFO",
            "Start process {0} on {1}".format(args.action, plog["hostname"]),
        )
        if args.action == "backup":
            # Write catalog file
            write_catalog(catalog_path, plog["id"], "start", utility.time_for_log())

    # Wait for jobs to complete before exiting
    while not all([p.ready() for p in jobs]):
        time.sleep(5)

    # Check exit code of command
    for p, command, plog in zip(jobs, commands, logs):
        if p.get() != 0:
            # Print warning for partial transfer
            if p.get() in (23, 24):
                utility.warning(
                    "Command {0} exit with code (partial transfer): {1}".format(
                        command, p.get()
                    ),
                    nocolor=args.color,
                )
                utility.write_log(
                    log_args["status"],
                    plog["destination"],
                    "WARNING",
                    "Finish process {0} on {1} with error (partial transfer):{2}".format(
                        args.action, plog["hostname"], p.get()
                    ),
                )
            else:
                utility.error(
                    "Command {0} exit with code: {1}".format(command, p.get()),
                    nocolor=args.color,
                )
                utility.write_log(
                    log_args["status"],
                    plog["destination"],
                    "ERROR",
                    "Finish process {0} on {1} with error:{2}".format(
                        args.action, plog["hostname"], p.get()
                    ),
                )
            if args.action == "backup":
                # Write catalog file
                write_catalog(catalog_path, plog["id"], "end", utility.time_for_log())
                write_catalog(catalog_path, plog["id"], "status", "{0}".format(p.get()))
                if args.retention and args.skip_err:
                    # Retention policy
                    retention_policy(
                        plog["hostname"], catalog_path, plog["destination"]
                    )
            # Retry
            necessaries_retries.append(command)

        else:
            utility.success("Command {0}".format(command), nocolor=args.color)
            utility.write_log(
                log_args["status"],
                plog["destination"],
                "INFO",
                "Finish process {0} on {1}".format(args.action, plog["hostname"]),
            )
            if args.action == "backup":
                # Write catalog file
                write_catalog(catalog_path, plog["id"], "end", utility.time_for_log())
                write_catalog(catalog_path, plog["id"], "status", "{0}".format(p.get()))
                if args.retention:
                    # Retention policy
                    retention_policy(
                        plog["hostname"], catalog_path, plog["destination"]
                    )

    # Safely terminate the pool
    pool.close()
    pool.join()

    return necessaries_retries


def start_process(command):
    """Start rsync commands

    :param command: rsync list command
    :return: command
    """
    fd = get_std_out()
    if fd == "STDOUT":
        p = subprocess.call(command, shell=True)
    else:
        p = subprocess.call(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    return p


def get_std_out():
    """Return stdout and stderr

    :return: string
    """
    global args

    if args.action == "backup":
        if args.list:
            stdout = "DEVNULL"
        elif args.hostname:
            if args.verbose:
                stdout = "STDOUT"
            else:
                stdout = "DEVNULL"
        else:
            stdout = "DEVNULL"
    elif args.action == "restore" or args.action == "export":
        if args.verbose:
            stdout = "STDOUT"
        else:
            stdout = "DEVNULL"
    else:
        stdout = "STDOUT"
    
    return stdout


def map_dict_folder(os_name):
    """Mapping folder structure to dictionary

    :param os_name: Name of operating system
    :return: Dictionary folder structure
    """
    # Set an empty dictionary folders
    folders = {}
    # Check operating system
    if os_name == "unix":
        folders["user"] = "/home"
        folders["config"] = "/etc"
        folders["application"] = "/usr"
        folders["system"] = "/"
        folders["log"] = "/var/log"
    elif os_name == "windows":
        folders["user"] = "/cygdrive/c/Users"
        folders["config"] = "/cygdrive/c/ProgramData"
        folders["application"] = "/cygdrive/c/Program Files"
        folders["system"] = "/cygdrive/c"
        folders["log"] = "/cygdrive/c/Windows/System32/winevt"
    elif os_name == "macos":
        folders["user"] = "/Users"
        folders["config"] = "/private/etc"
        folders["application"] = "/Applications"
        folders["system"] = "/"
        folders["log"] = "/private/var/log"
    # Return dictionary with folder structure
    return folders


def compose_command(flags, host):
    """Compose rsync command for action

    :param flags: Dictionary than contains info for command
    :param host: Hostname of machine
    :return: list
    """
    global args, catalog_path, backup_id, rpath, hostname

    utility.print_verbose(args.verbose, "Build a rsync command", nocolor=args.color)
    command = ["rsync"]
    # Set rsync binary
    if flags.rsync:
        if os.path.exists(flags.rsync):
            command = [flags.rsync]
        else:
            utility.warning(
                "rsync binary {0} not exist! Set default.".format(args.rsync),
                nocolor=args.color,
            )
    catalog = read_catalog(catalog_path)
    if flags.action == "backup":
        # Set mode option
        if flags.mode == "full":
            command.append("-ah")
            # Write catalog file
            write_catalog(catalog_path, backup_id, "type", "full")
        elif flags.mode == "incremental":
            last_bck = get_last_backup(catalog)
            if last_bck:
                command.append("-ahu")
                if not flags.sfrom:
                    command.append("--link-dest={0}".format(last_bck[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, "type", "incremental")
            else:
                command.append("-ah")
                # Write catalog file
                write_catalog(catalog_path, backup_id, "type", "full")
        elif flags.mode == "differential":
            last_full = get_last_full(catalog)
            if last_full:
                command.append("-ahu")
                if not flags.sfrom:
                    command.append("--link-dest={0}".format(last_full[0]))
                # Write catalog file
                write_catalog(catalog_path, backup_id, "type", "differential")
            else:
                command.append("-ah")
                # Write catalog file
                write_catalog(catalog_path, backup_id, "type", "full")
        elif flags.mode == "mirror":
            command.append("-ah")
            command.append("--delete")
            # Write catalog file
            write_catalog(catalog_path, backup_id, "type", "mirror")
        command.append("--no-links")
        # Set dry-run mode
        if flags.dry_run:
            command.append("--dry-run")
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "dry-run mode activate",
            )
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append("--exclude={0}".format(exclude))
        if flags.log:
            log_path = os.path.join(
                compose_destination(host, flags.destination), "backup.log"
            )
            command.append("--log-file={0}".format(log_path))
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "rsync log path: {0}".format(log_path),
            )
    elif flags.action == "restore":
        command.append("-ahu")
        if not args.acl:
            command.append("--no-perms --no-owner --no-group")
        if flags.verbose:
            command.append("-vP")
            # Set quite mode
        if flags.skip_err:
            command.append("--quiet")
        # Set I/O timeout
        if flags.timeout:
            command.append("--timeout={0}".format(flags.timeout))
        # Set mirror mode
        if flags.mirror:
            command.append("--delete")
        # Set bandwidth limit
        if flags.bwlimit:
            command.append("--bwlimit={0}".format(flags.bwlimit))
        # Set ssh custom port
        if flags.port:
            command.append('--rsh "ssh -p {0}"'.format(flags.port))
        # Set dry-run mode
        if flags.dry_run:
            command.append("--dry-run")
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "dry-run mode activate",
            )
        # Set excludes
        if flags.exclude:
            for exclude in flags.exclude:
                command.append("--exclude={0}".format(exclude))
        if flags.log:
            log_path = os.path.join(rpath, "restore.log")
            command.append("--log-file={0}".format(log_path))
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "rsync log path: {0}".format(log_path),
            )
    elif flags.action == "export":
        command.append("-ahu")
        # Set mirror mode
        if flags.mirror:
            command.append("--delete")
        # Set cut mode
        if flags.cut:
            command.append("--remove-source-files")
        # No copy symbolic link
        if flags.all:
            command.append("--safe-links")
        # Make hard links to specific path
        if flags.link:
            command.append("--link-dest={0}".format(flags.link))
        # Set dry-run mode
        if flags.dry_run:
            command.append("--dry-run")
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "dry-run mode activate",
            )
        if flags.log:
            log_path = os.path.join(flags.catalog, "export.log")
            command.append("--log-file={0}".format(log_path))
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "rsync log path: {0}".format(log_path),
            )
    utility.print_verbose(
        args.verbose,
        "Command flags are: {0}".format(" ".join(command)),
        nocolor=args.color,
    )
    # Common rsync flags
    if not args.acl:
        command.append("--no-perms --no-owner --no-group")
    # Set verbosity
    if flags.verbose:
        command.append("-vP")
        command.append("--stats")
    # Set quite mode
    if flags.skip_err:
        command.append("--quiet")
    # Set compress mode
    if flags.compress:
        command.append("-z")
    # Set bandwidth limit
    if flags.bwlimit:
        command.append("--bwlimit={0}".format(flags.bwlimit))
    # Set ssh custom port
    if flags.port:
        command.append('--rsh "ssh -p {0}"'.format(flags.port))
    # Set I/O timeout
    if flags.timeout:
        command.append("--timeout={0}".format(flags.timeout))
    if flags.checksum:
        command.append("--checksum")
    if flags.links:
        command.append("--links")
    # Set includes
    if flags.include:
        for include in flags.include:
            command.append("--include={0}".format(include))
            command.append('--exclude="*"')
    # Set excludes
    elif flags.exclude:
        for exclude in flags.exclude:
            command.append("--exclude={0}".format(exclude))
    return command


def compose_source():
    """Compose sources

    :return: list
    """
    global args, catalog_path, backup_id

    src_list = []
    # Add include to the list
    if args.data:
        folders = map_dict_folder(args.type)
        if "system" in args.data:
            src_list.append(":'{0}'".format(folders["system"]))
            return src_list
        if "user" in args.data:
            src_list.append(":'{0}'".format(folders["user"]))
        if "config" in args.data:
            src_list.append(":'{0}'".format(folders["config"]))
        if "application" in args.data:
            src_list.append(":'{0}'".format(folders["application"]))
        if "log" in args.data:
            src_list.append(":'{0}'".format(folders["log"]))
    elif args.customdata:
        # This is the custom data
        for custom_data in args.customdata:
            src_list.append(":'{0}'".format(custom_data.strip()))
    elif args.filedata:
        # This is the file custom data
        with args.filedata as file_data:
            for path in file_data.readlines():
                src_list.append(":'{0}'".format(path.strip()))
    utility.write_log(
        log_args["status"],
        log_args["destination"],
        "INFO",
        "OS {0}; backup folder {1}".format(args.type, " ".join(src_list)),
    )
    utility.print_verbose(
        args.verbose,
        "Include this criteria: {0}".format(" ".join(src_list)),
        nocolor=args.color,
    )
    return src_list


def compose_restore_src_dst(backup_os, restore_os, restore_path):
    """Compare dictionary of folder backup and restore

    :param backup_os: backup structure folders
    :param restore_os: restore structure folders
    :param restore_path: path of backup
    :return: set
    """
    global args

    # Compare folder of the backup os and restore os
    b_folders = map_dict_folder(backup_os)
    r_folders = map_dict_folder(restore_os)
    for key in b_folders.keys():
        if restore_path in b_folders[key]:
            rsrc = os.path.join(restore_path, "*")
            rdst = r_folders[key]
        elif args.root_dir:
            rsrc = restore_path
            rdst = (
                os.path.join("/", args.root_dir)
                if not args.root_dir.startswith("/")
                else args.root_dir
            )
        else:
            rsrc = restore_path
            rdst = os.path.join(
                r_folders["system"], "restore_{0}".format(utility.time_for_folder())
            )
    if rsrc and rdst:
        return rsrc, rdst
    else:
        return ()


def get_restore_os():
    """Get the operating system value on catalog by id

    :return: os value (string)
    """
    global args, catalog_file

    config = read_catalog(os.path.join(args.catalog, catalog_file))
    return config.get(args.id, "os")


def compose_destination(computer_name, folder):
    """Compose folder destination of backup

    :param computer_name: name of source computer
    :param folder: path of backup
    :return: string
    """
    # Create root folder of backup
    first_layer = os.path.join(folder, computer_name)
    # Check if backup is a Mirror or not
    if args.mode != "mirror":
        second_layer = os.path.join(first_layer, utility.time_for_folder())
    else:
        second_layer = os.path.join(first_layer, "mirror_backup")
    if not os.path.exists(first_layer):
        os.mkdir(first_layer)
        utility.write_log(
            log_args["status"],
            log_args["destination"],
            "INFO",
            "Create folder {0}".format(first_layer),
        )
    if not os.path.exists(second_layer):
        os.mkdir(second_layer)
        utility.write_log(
            log_args["status"],
            log_args["destination"],
            "INFO",
            "Create folder {0}".format(second_layer),
        )
    # Write catalog file
    write_catalog(catalog_path, backup_id, "path", second_layer)
    return second_layer


def get_last_full(catalog):
    """Get the last full

    :param catalog: configparser object
    :return: path (string), os (string)
    """
    global hostname, args

    config = catalog
    if config:
        dates = []
        for bid in config.sections():
            if (
                config.get(bid, "type") == "full"
                and config.get(bid, "name") == hostname
                and (
                    not config.has_option(bid, "cleaned")
                    or not config.has_option(bid, "archived")
                )
            ):
                try:
                    dates.append(utility.string_to_time(config.get(bid, "timestamp")))
                except configparser.NoOptionError:
                    utility.error(
                        "Corrupted catalog! No found timestamp in {0}".format(bid),
                        nocolor=args.color,
                    )
                    exit(2)
        if dates:
            last_full = utility.time_to_string(max(dates))
            if last_full:
                utility.print_verbose(
                    args.verbose,
                    "Last full backup is {0}".format(last_full),
                    nocolor=args.color,
                )
                for bid in config.sections():
                    if (
                        config.get(bid, "type") == "full"
                        and config.get(bid, "name") == hostname
                        and config.get(bid, "timestamp") == last_full
                    ):
                        return config.get(bid, "path"), config.get(bid, "os")
                return ()
    else:
        return ()


def get_last_backup(catalog):
    """Get the last available backup

    :param catalog: configparser object
    :return: path (string), os (string)
    """
    global hostname, args

    config = catalog
    dates = []
    if config:
        for bid in config.sections():
            if config.get(bid, "name") == hostname and (
                not config.has_option(bid, "cleaned")
                or not config.has_option(bid, "archived")
            ):
                try:
                    dates.append(utility.string_to_time(config.get(bid, "timestamp")))
                except configparser.NoOptionError:
                    utility.error(
                        "Corrupted catalog! No found timestamp in backup: {0}".format(
                            bid
                        ),
                        nocolor=args.color,
                    )
                    exit(2)
        if dates:
            dates.sort()
            last = utility.time_to_string(dates[-1])
            if last:
                utility.print_verbose(
                    args.verbose,
                    "Last backup is {0}".format(last),
                    nocolor=args.color,
                )
                for bid in config.sections():
                    if (
                        config.get(bid, "name") == hostname
                        and config.get(bid, "timestamp") == last
                    ):
                        return config.get(bid, "path"), config.get(bid, "os"), bid
                return ()
    else:
        return ()


def count_full(config, name):
    """Count all full (and Incremental) backup in a catalog

    :param config: configparser object
    :param name: hostname of machine
    :return: count (int)
    """
    count = 0
    if config:
        for bid in config.sections():
            if (
                config.get(bid, "type") == "full"
                or config.get(bid, "type") == "incremental"
            ) and config.get(bid, "name") == name:
                count += 1
    return count


def list_backup(config, name):
    """Count all full in a catalog

    :param config: configparser object
    :param name: hostname of machine
    :return: r_list (list)
    """
    r_list = list()
    if config:
        for bid in config.sections():
            if config.get(bid, "name") == name:
                r_list.append(bid)
    return r_list


def read_catalog(catalog):
    """Read a catalog file

    :param catalog: catalog file
    :return: catalog file (configparser)
    """
    global args

    config = configparser.ConfigParser()
    file = config.read(catalog)
    if file:
        return config
    else:
        utility.print_verbose(
            args.verbose, "Catalog not found! Create a new one.", nocolor=args.color
        )
        if os.path.exists(os.path.dirname(catalog)):
            utility.touch(catalog)
            config.read(catalog)
            return config
        else:
            utility.error(
                "Folder {0} not exist!".format(os.path.dirname(catalog)),
                nocolor=args.color,
            )
            exit(1)


def write_catalog(catalog, section, key, value):
    """Write catalog file

    :param catalog: path catalog file
    :param section: section of catalog file
    :param key: key of catalog file
    :param value: value of key of catalog file
    :return:
    """
    global args

    config = read_catalog(catalog)
    if not args.dry_run:
        # Add new section
        try:
            config.add_section(section)
            config.set(section, key, value)
        except configparser.DuplicateSectionError:
            config.set(section, key, value)
        # Write new section
        with open(catalog, "w") as configfile:
            config.write(configfile)


def retention_policy(host, catalog, logpath):
    """Retention policy

    :param host: hostname of machine
    :param catalog: catalog file
    :param logpath: path of log file
    """
    global args

    config = read_catalog(catalog)
    full_count = count_full(config, host)
    if len(args.retention) == 2:
        backup_list = list_backup(config, host)[-args.retention[1] :]
    else:
        backup_list = list()
    cleanup = -1
    for bid in config.sections():
        if bid not in backup_list:
            if (config.get(bid, "cleaned", fallback="unset") == "unset") and (
                config.get(bid, "name") == host
            ):
                type_backup = config.get(bid, "type")
                path = config.get(bid, "path")
                date = config.get(bid, "timestamp")
                if (type_backup == "full" or type_backup == "incremental") and (
                    full_count <= 1
                ):
                    continue
                utility.print_verbose(
                    args.verbose,
                    "Check cleanup this backup {0}. Folder {1}".format(bid, path),
                    nocolor=args.color,
                )
                if not dry_run("Cleanup {0} backup folder".format(path)):
                    cleanup = utility.cleanup(path, date, args.retention[0])
                if not os.path.exists(path):
                    utility.print_verbose(
                        args.verbose,
                        "This folder {0} does not exist. "
                        "The backup has already been cleaned.".format(path),
                        nocolor=args.color,
                    )
                    cleanup = 0
                if cleanup == 0:
                    write_catalog(catalog, bid, "cleaned", "True")
                    utility.success(
                        "Cleanup {0} successfully.".format(path), nocolor=args.color
                    )
                    utility.write_log(
                        log_args["status"],
                        logpath,
                        "INFO",
                        "Cleanup {0} successfully.".format(path),
                    )
                    utility.unlink(os.path.join(catalog, host, "last_backup"))
                elif cleanup == 1:
                    utility.error(
                        "Cleanup {0} failed.".format(path), nocolor=args.color
                    )
                    utility.write_log(
                        log_args["status"],
                        logpath,
                        "ERROR",
                        "Cleanup {0} failed.".format(path),
                    )
                else:
                    utility.print_verbose(
                        args.verbose,
                        "No cleanup backup {0}. Folder {1}".format(bid, path),
                        nocolor=args.color,
                    )


def archive_policy(catalog, destination):
    """Archive policy

    :param catalog: catalog file
    :param destination: destination pth of archive file
    """
    global args

    config = read_catalog(catalog)
    archive = -1
    for bid in config.sections():
        full_count = count_full(config, config.get(bid, "name"))
        if (config.get(bid, "archived", fallback="unset") == "unset") and not (
            config.get(bid, "cleaned", fallback=False)
        ):
            type_backup = config.get(bid, "type")
            path = config.get(bid, "path")
            date = config.get(bid, "timestamp")
            logpath = os.path.join(os.path.dirname(path), "general.log")
            utility.print_verbose(
                args.verbose,
                "Check archive this backup {0}. Folder {1}".format(bid, path),
                nocolor=args.color,
            )
            if (type_backup == "full") and (full_count <= 1):
                continue
            if not dry_run("Archive {0} backup folder".format(path)):
                archive = utility.archive(path, date, args.days, destination)
            if archive == 0:
                write_catalog(catalog, bid, "archived", "True")
                utility.success(
                    "Archive {0} successfully.".format(path), nocolor=args.color
                )
                utility.write_log(
                    log_args["status"],
                    logpath,
                    "INFO",
                    "Archive {0} successfully.".format(path),
                )
            elif archive == 1:
                utility.error("Archive {0} failed.".format(path), nocolor=args.color)
                utility.write_log(
                    log_args["status"],
                    logpath,
                    "ERROR",
                    "Archive {0} failed.".format(path),
                )
            else:
                utility.print_verbose(
                    args.verbose,
                    "No archive backup {0}. Folder {1}".format(bid, path),
                    nocolor=args.color,
                )


def deploy_configuration(computer, user):
    """Deploy configuration (public key) on remote machine

    (run "ssh-copy-id -i pub_file -f <user>@<computer>")
    :param computer: remote computer to deploy public key to
    :param user: remote user on computer
    :param keytype: type of key to use ( rsa or ed25519 )
    """
    global args

    # Create home path
    home = os.path.expanduser("~")
    ssh_folder = os.path.join(home, ".ssh")
    keytype = args.keytype

    # Remove private key file
    id_key_pub_file = os.path.join(ssh_folder, "id_{0}.pub".format(keytype))
    utility.print_verbose(
        args.verbose,
        "Public key file is {0}".format(id_key_pub_file),
        nocolor=args.color,
    )
    if not dry_run("Copying configuration to {0}".format(computer)):
        if os.path.exists(id_key_pub_file):
            print(
                "info: Copying configuration to {0}".format(computer)
                + "; write the password:"
            )
            return_code = subprocess.call(
                "ssh-copy-id -i {0} {1}@{2}".format(id_key_pub_file, user, computer),
                shell=True,
            )
            utility.print_verbose(
                args.verbose,
                "Return code of ssh-copy-id: {0}".format(return_code),
                nocolor=args.color,
            )
            if return_code == 0:
                utility.success(
                    "Configuration copied successfully on {0}!".format(computer),
                    nocolor=args.color,
                )
            else:
                utility.error(
                    "Configuration has not been copied successfully on {0}!".format(
                        computer
                    ),
                    nocolor=args.color,
                )
                exit(2)
        else:
            utility.warning(
                "Public key ~/.ssh/id_{0}.pub is not exist".format(keytype),
                nocolor=args.color,
            )
            exit(2)


def remove_configuration():
    """Remove a new configuration (remove an existing public/private key pair)"""
    global args

    # Create home path
    home = os.path.expanduser("~")
    ssh_folder = os.path.join(home, ".ssh")
    keytype = args.keytype

    if not dry_run("Remove private id_{0}".format(keytype)):
        if utility.confirm(
            "info: Are you sure to remove existing {0} keys?".format(keytype),
            force=args.force,
        ):
            # Remove private key file
            id_key_file = os.path.join(ssh_folder, "id_{0}".format(keytype))
            utility.print_verbose(
                args.verbose,
                "Remove private key file {0}".format(id_key_file),
                nocolor=args.color,
            )
            if os.path.exists(id_key_file):
                os.remove(id_key_file)
            else:
                utility.warning(
                    "Private key ~/.ssh/id_{0} is not exist".format(keytype),
                    nocolor=args.color,
                )
                exit(2)
            # Remove public key file
            id_key_pub_file = os.path.join(ssh_folder, "id_{0}.pub".format(keytype))
            utility.print_verbose(
                args.verbose,
                "Remove public key file {0}".format(id_key_pub_file),
                nocolor=args.color,
            )
            if os.path.exists(id_key_pub_file):
                os.remove(id_key_pub_file)
            else:
                utility.warning(
                    "Public key ~/.ssh/id_{0}.pub is not exist".format(keytype),
                    nocolor=args.color,
                )
                exit(2)
            utility.success("Removed configuration successfully!", nocolor=args.color)


def new_configuration():
    """Create a new configuration (create a public/private key pair)"""
    global args

    # Create home path
    home = os.path.expanduser("~")
    ssh_folder = os.path.join(home, ".ssh")
    keytype = args.keytype
    id_key_file = os.path.join(ssh_folder, "id_{0}".format(keytype))
    if not dry_run("Generate private/public key pair"):
        # Generate private/public key pair
        utility.print_verbose(
            args.verbose,
            "Generate private/public key pair of type {0}".format(keytype),
            nocolor=args.color,
        )
        return_code = subprocess.call(
            [
                "ssh-keygen",
                "-t",
                "{0}".format(keytype),
                "-b",
                "4096",
                "-N",
                "{0}".format(""),
                "-f",
                "{0}".format(id_key_file),
                "-q",
            ]
        )
        utility.print_verbose(
            args.verbose,
            "Return code of ssh-keygen: {0}".format(return_code),
            nocolor=args.color,
        )
        # Check if something wrong
        if return_code:
            utility.error(
                "Creation of {0} error".format(id_key_file), nocolor=args.color
            )
            exit(2)
        # Sucess!
        utility.success("New configuration successfully created!", nocolor=args.color)


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
    return True


def init_catalog(catalog):
    """Initialize catalog file

    :param catalog: catalog file
    """
    global args

    if utility.confirm(
        "info: Initialize catalog {0}?".format(catalog), force=args.force
    ):
        config = read_catalog(catalog)
        for cid in config.sections():
            if not config.get(cid, "path") or not os.path.exists(
                config.get(cid, "path")
            ):
                utility.print_verbose(
                    args.verbose,
                    "Backup-id {0} has been removed to catalog!".format(cid),
                    nocolor=args.color,
                )
                config.remove_section(cid)
        # Write file
        with open(catalog, "w") as configfile:
            config.write(configfile)


def delete_host(catalog, host):
    """:param catalog: catalog file

    :param host: hostname or ip address
    """
    global args

    from shutil import rmtree

    config = read_catalog(catalog)
    root = os.path.join(os.path.dirname(catalog), host)
    if utility.confirm(
        "info: Delete all backups for host {0}?".format(host), force=args.force
    ):
        for cid in config.sections():
            if config.get(cid, "name") == host:
                if not config.get(cid, "path") or not os.path.exists(
                    config.get(cid, "path")
                ):
                    utility.print_verbose(
                        args.verbose,
                        "Backup-id {0} has been removed from catalog!".format(cid),
                        nocolor=args.color,
                    )
                    config.remove_section(cid)
                else:
                    path = config.get(cid, "path")
                    date = config.get(cid, "timestamp")
                    cleanup = utility.cleanup(path, date, 0)
                    if cleanup == 0:
                        utility.success(
                            "Delete {0} successfully.".format(path), nocolor=args.color
                        )
                        utility.print_verbose(
                            args.verbose,
                            "Backup-id {0} has been removed from catalog!".format(cid),
                            nocolor=args.color,
                        )
                        config.remove_section(cid)
                    elif cleanup == 1:
                        utility.error(
                            "Delete {0} failed.".format(path), nocolor=args.color
                        )
        # Remove root folder
        if os.path.exists(root):
            rmtree(root)
        # Write file
        with open(catalog, "w") as configfile:
            config.write(configfile)


def delete_backup(catalog, bckid):
    """Delete selected backup by id

    :param catalog: catalog file
    :param bckid: backup id
    """
    global args

    config = read_catalog(catalog)
    # Check catalog backup id
    bck_id = utility.get_bckid(config, bckid)
    if utility.confirm(
        "info: Delete backup {0} from catalog {1}?".format(bckid, catalog),
        force=args.force,
    ):
        if bck_id:
            if not bck_id.get("path") or not os.path.exists(bck_id.get("path")):
                utility.print_verbose(
                    args.verbose,
                    "Backup-id {0} has been removed from catalog!".format(bckid),
                    nocolor=args.color,
                )
                config.remove_section(bck_id.name)
            else:
                path = bck_id.get("path")
                date = bck_id.get("timestamp")
                cleanup = utility.cleanup(path, date, 0)
                if cleanup == 0:
                    utility.success(
                        "Delete {0} successfully.".format(path), nocolor=args.color
                    )
                    utility.print_verbose(
                        args.verbose,
                        "Backup-id {0} has been removed from catalog!".format(bckid),
                        nocolor=args.color,
                    )
                    config.remove_section(bck_id.name)
                elif cleanup == 1:
                    utility.error("Delete {0} failed.".format(path), nocolor=args.color)
        # Write file
        with open(catalog, "w") as configfile:
            config.write(configfile)


def clean_catalog(catalog):
    """Clean catalog by archived/deleted backup

    :param catalog: catalog file
    """
    global args

    config = read_catalog(catalog)
    utility.print_verbose(
        args.verbose,
        "Start check catalog file: {0}!".format(catalog),
        nocolor=args.color,
    )
    for cid in config.sections():
        utility.print_verbose(
            args.verbose, "Check backup-id: {0}!".format(cid), nocolor=args.color
        )
        mod = False
        if not config.get(cid, "type", fallback=""):
            config.set(cid, "type", "incremental")
            mod = True
        if not config.get(cid, "path", fallback=""):
            config.remove_section(cid)
            mod = True
        if not config.get(cid, "name", fallback=""):
            config.set(cid, "name", "default")
            mod = True
        if not config.get(cid, "os", fallback=""):
            config.set(cid, "os", "unix")
            mod = True
        if not config.get(cid, "timestamp", fallback=""):
            config.set(cid, "timestamp", utility.time_for_log())
            mod = True
        if not config.get(cid, "start", fallback=""):
            config.set(cid, "start", utility.time_for_log())
            mod = True
        if not config.get(cid, "end", fallback=""):
            config.set(cid, "end", utility.time_for_log())
            mod = True
        if not config.get(cid, "status", fallback=""):
            config.set(cid, "status", "0")
            mod = True
        if mod:
            utility.warning(
                "The backup-id {0} has been set to default value, "
                "because he was corrupt. "
                "Check it!".format(cid),
                nocolor=args.color,
            )
    # Write file
    with open(catalog, "w") as configfile:
        config.write(configfile)


def get_files(bckid, files):
    """Get list of files"""
    # Get path from id
    path = bckid.get("path")
    if path:
        # Search files into backup folder
        return [f for file in files for f in glob("{0}/**/*{1}*".format(path, file))]
    else:
        return []


def parse_arguments():
    """Get arguments from command line

    :return: argument
    """
    global VERSION

    # Create a common parser
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "--verbose", "-v", help="Enable verbosity", dest="verbose", action="store_true"
    )
    parent_parser.add_argument(
        "--log", "-l", help="Create logs", dest="log", action="store_true"
    )
    parent_parser.add_argument(
        "--dry-run", "-N", help="Dry run mode", dest="dry_run", action="store_true"
    )
    parent_parser.add_argument(
        "--force",
        "-O",
        help="Force an action without prompt",
        dest="force",
        action="store_true",
    )
    parent_parser.add_argument(
        "--no-color",
        "-w",
        help="Remove color into terminal",
        dest="color",
        action="store_true",
    )
    parent_parser.add_argument(
        "--explain-error",
        "-x",
        help="Print python traceback",
        dest="error",
        action="store_true",
    )

    parent_parser.add_argument(
        "--keytype",
        "-k",
        help="Kind of public/private key to use or generate",
        dest="keytype",
        action="store",
        choices=["rsa", "ed25519"],
        default="rsa",
    )

    # Rsync parser
    rsync_parser = argparse.ArgumentParser(
        add_help=False,
        description="Rsync options",
    )
    rsync_group = rsync_parser.add_argument_group(title="Rsync options")
    rsync_group.add_argument(
        "--compress", "-z", help="Compress data", dest="compress", action="store_true"
    )
    rsync_group.add_argument(
        "--timeout",
        "-T",
        help="I/O timeout in seconds",
        dest="timeout",
        action="store",
        type=int,
        metavar="SECONDS",
    )
    rsync_group.add_argument(
        "--skip-error", "-e", help="Skip error", dest="skip_err", action="store_true"
    )
    rsync_group.add_argument(
        "--rsync-path",
        "-R",
        help="Custom rsync path",
        dest="rsync",
        action="store",
        metavar="PATH",
    )
    rsync_group.add_argument(
        "--bwlimit",
        "-b",
        help="Bandwidth limit in KBPS.",
        dest="bwlimit",
        action="store",
        type=int,
    )
    rsync_group.add_argument(
        "--ssh-port",
        "-P",
        help="Custom ssh port.",
        dest="port",
        action="store",
        type=int,
    )
    pattern_rsync_mutually = rsync_group.add_mutually_exclusive_group()
    pattern_rsync_mutually.add_argument(
        "--include",
        "-I",
        help="Include pattern",
        dest="include",
        action="store",
        nargs="+",
        metavar="PATTERN",
    )
    pattern_rsync_mutually.add_argument(
        "--exclude",
        "-E",
        help="Exclude pattern",
        dest="exclude",
        action="store",
        nargs="+",
        metavar="PATTERN",
    )
    rsync_group.add_argument(
        "--checksum",
        "-S",
        help="Checks if the files have been changed",
        dest="checksum",
        action="store_true",
    )
    rsync_group.add_argument(
        "--links",
        "-K",
        help="Preserve symbolic links",
        dest="links",
        action="store_true",
    )
    rsync_group.add_argument(
        "--acl", "-a", help="Preserve ACLs", dest="acl", action="store_true"
    )
    rsync_group.add_argument(
        "--files",
        "-f",
        help="Consider only specified files",
        dest="files",
        action="store",
        nargs="+",
    )
    rsync_group.add_argument(
        "--retry",
        "-U",
        help="Number of retries action",
        dest="retry",
        action="store",
        metavar="NUMBER",
        type=int,
        default=0,
    )
    rsync_group.add_argument(
        "--wait",
        "-W",
        help="Wait seconds to start an action",
        dest="wait",
        action="store",
        metavar="SECONDS",
        type=int,
        default=0,
    )
    rsync_group.add_argument(
        "--user",
        "-u",
        help="Login name used to log into the remote host",
        dest="user",
        action="store",
        default=getpass.getuser(),
    )

    # Create principal parser
    description = "Butterfly Backup"
    parser_object = argparse.ArgumentParser(
        prog="bb",
        description=description,
        parents=[parent_parser],
    )
    parser_object.add_argument(
        "--version",
        "-V",
        help="Print version",
        action="version",
        version="%(prog)s " + VERSION,
    )

    # Create sub_parser "action"
    action = parser_object.add_subparsers(
        title="action",
        description="Valid action",
        help="Available actions",
        dest="action",
        required=True,
    )
    # config session
    config = action.add_parser(
        "config", help="Configuration options", parents=[parent_parser]
    )
    group_config = config.add_argument_group(title="Init configuration")

    group_config_mutually = group_config.add_mutually_exclusive_group()
    group_config_mutually.add_argument(
        "--new",
        "-n",
        help="Generate new configuration",
        dest="new_conf",
        action="store_true",
    )
    group_config_mutually.add_argument(
        "--remove",
        "-r",
        help="Remove exist configuration",
        dest="remove_conf",
        action="store_true",
    )
    group_config_mutually.add_argument(
        "--init",
        "-i",
        help="Reset CATALOG file. Specify path of backup folder.",
        dest="init",
        metavar="CATALOG",
        action="store",
    )
    group_config_mutually.add_argument(
        "--delete-host",
        "-D",
        help="Delete all entry for a single HOST in CATALOG.",
        nargs=2,
        dest="delete",
        metavar=("CATALOG", "HOST"),
        action="store",
    )
    group_config_mutually.add_argument(
        "--clean",
        "-c",
        help="Cleans the CATALOG if it is corrupt, setting default values.",
        dest="clean",
        metavar="CATALOG",
        action="store",
    )
    group_config_mutually.add_argument(
        "--delete-backup",
        "-b",
        nargs=2,
        help="Delete specific backup ID from CATALOG",
        metavar=("CATALOG", "ID"),
        action="store",
    )
    group_deploy = config.add_argument_group(title="Deploy configuration")
    group_deploy_mutually = group_deploy.add_mutually_exclusive_group()
    group_deploy_mutually.add_argument(
        "--deploy",
        "-d",
        help="Deploy configuration to client: hostname or ip address",
        dest="deploy_host",
        action="store",
    )
    group_deploy.add_argument(
        "--user",
        "-u",
        help="User of the remote machine",
        dest="deploy_user",
        action="store",
        default=getpass.getuser(),
    )
    # backup session
    backup = action.add_parser(
        "backup", help="Backup options", parents=[parent_parser, rsync_parser]
    )
    group_backup = backup.add_argument_group(title="Backup options")
    single_or_list_group = group_backup.add_mutually_exclusive_group(required=True)
    single_or_list_group.add_argument(
        "--computer",
        "-c",
        help="Hostname or ip address to backup",
        dest="hostname",
        action="store",
    )
    single_or_list_group.add_argument(
        "--list",
        "-L",
        help="File list of computers or ip addresses to backup",
        dest="list",
        action="store",
    )
    group_backup.add_argument(
        "--destination",
        "-d",
        help="Destination path (catalog)",
        dest="destination",
        action="store",
        required=True,
        metavar="CATALOG",
    )
    group_backup.add_argument(
        "--mode",
        "-m",
        help="Backup mode",
        dest="mode",
        action="store",
        choices=["full", "incremental", "differential", "mirror"],
        default="incremental",
        type=str.lower,
    )
    data_or_custom = group_backup.add_mutually_exclusive_group(required=True)
    data_or_custom.add_argument(
        "--data",
        "-D",
        help="Data of which you want to backup",
        dest="data",
        action="store",
        choices=["user", "config", "application", "system", "log"],
        nargs="+",
        type=str.lower,
    )
    data_or_custom.add_argument(
        "--custom-data",
        "-C",
        help="Custom path of which you want to backup",
        dest="customdata",
        action="store",
        nargs="+",
        metavar="PATHS",
    )
    data_or_custom.add_argument(
        "--file-data",
        "-F",
        help="File with custom path of which you want to backup",
        dest="filedata",
        action="store",
        type=argparse.FileType(),
    )
    group_backup.add_argument(
        "--type",
        "-t",
        help="Type of operating system to backup",
        dest="type",
        action="store",
        choices=["unix", "windows", "macos"],
        required=True,
        type=str.lower,
    )
    group_backup.add_argument(
        "--retention",
        "-r",
        help="First argument are days of backup retention. "
        "Second argument is minimum number "
        "of backup retention",
        dest="retention",
        action="store",
        nargs="*",
        metavar="DAYS [NUMBER]",
        type=int,
    )
    group_backup.add_argument(
        "--parallel",
        "-p",
        help="Number of parallel backups",
        dest="parallel",
        action="store",
        type=int,
        default=4,
        metavar="NUMBER",
    )
    group_backup.add_argument(
        "--start-from",
        "-s",
        help="Backup id where start a new backup",
        dest="sfrom",
        action="store",
        metavar="ID",
    )
    # restore session
    restore = action.add_parser(
        "restore", help="Restore options", parents=[parent_parser, rsync_parser]
    )
    group_restore = restore.add_argument_group(title="Restore options")
    group_restore.add_argument(
        "--catalog",
        "-C",
        help="Catalog path",
        dest="catalog",
        action="store",
        required=True,
    )
    restore_id_or_last = group_restore.add_mutually_exclusive_group(required=True)
    restore_id_or_last.add_argument(
        "--backup-id",
        "-i",
        help="Backup-id of backup",
        dest="id",
        action="store",
        metavar="ID",
    )
    restore_id_or_last.add_argument(
        "--last",
        "-L",
        help="Last available backup of the same host",
        dest="last",
        action="store_true",
    )
    group_restore.add_argument(
        "--computer",
        "-c",
        help="Hostname or ip address to perform restore",
        dest="hostname",
        action="store",
        required=True,
    )
    group_restore.add_argument(
        "--root-dir",
        "-r",
        help="Root directory to perform restore",
        dest="root_dir",
        action="store",
        metavar="PATH",
    )
    group_restore.add_argument(
        "--type",
        "-t",
        help="Type of operating system to perform restore",
        dest="type",
        action="store",
        choices=["unix", "windows", "macos"],
        type=str.lower,
    )
    group_restore.add_argument(
        "--mirror", "-m", help="Mirror mode", dest="mirror", action="store_true"
    )
    # archive session
    archive = action.add_parser(
        "archive", help="Archive options", parents=[parent_parser]
    )
    group_archive = archive.add_argument_group(title="Archive options")
    group_archive.add_argument(
        "--catalog",
        "-C",
        help="Catalog path",
        dest="catalog",
        action="store",
        required=True,
    )
    group_archive.add_argument(
        "--days",
        "-D",
        help="Number of days of archive retention",
        dest="days",
        action="store",
        type=int,
        default=30,
    )
    group_archive.add_argument(
        "--destination",
        "-d",
        help="Archive destination path",
        dest="destination",
        action="store",
        required=True,
        metavar="PATH",
    )
    # list session
    list_action = action.add_parser(
        "list", help="List options", parents=[parent_parser]
    )
    group_list = list_action.add_argument_group(title="List options")
    group_list.add_argument(
        "--catalog",
        "-C",
        help="Catalog path",
        dest="catalog",
        action="store",
        required=True,
    )
    group_list_mutually = group_list.add_mutually_exclusive_group()
    group_list_mutually.add_argument(
        "--backup-id",
        "-i",
        help="Backup-id of backup",
        dest="id",
        action="store",
        metavar="ID",
    )
    group_list_mutually.add_argument(
        "--archived",
        "-a",
        help="List only archived backup",
        dest="archived",
        action="store_true",
    )
    group_list_mutually.add_argument(
        "--cleaned",
        "-c",
        help="List only cleaned backup",
        dest="cleaned",
        action="store_true",
    )
    group_list_mutually.add_argument(
        "--last",
        "-L",
        help="Only last backup",
        dest="last",
        action="store_true",
    )
    group_list_mutually.add_argument(
        "--detail",
        "-d",
        help="List detail of file and folder of specific backup-id",
        dest="detail",
        action="store",
        metavar="ID",
    )
    group_list_mutually.add_argument(
        "--status",
        "-S",
        help="Only backup(s) of specific status number",
        dest="status",
        action="store",
        metavar="NUMBER",
        type=int,
    )
    group_list.add_argument(
        "--oneline", "-o", help="One line output", dest="oneline", action="store_true"
    )
    group_list.add_argument(
        "--computer",
        "-H",
        help="List only match hostname or ip",
        dest="hostname",
        action="store",
    )
    group_list.add_argument(
        "--only-id",
        "-y",
        help="List only id",
        dest="ids",
        action="store_true",
    )
    # export session
    export_action = action.add_parser(
        "export", help="Export options", parents=[parent_parser, rsync_parser]
    )
    group_export = export_action.add_argument_group(title="Export options")
    group_export.add_argument(
        "--catalog",
        "-C",
        help="Catalog path",
        dest="catalog",
        action="store",
        required=True,
    )
    group_export_id_or_all = group_export.add_mutually_exclusive_group()
    group_export_id_or_all.add_argument(
        "--backup-id",
        "-i",
        help="Backup-id of backup",
        dest="id",
        action="store",
        metavar="ID",
    )
    group_export_id_or_all.add_argument(
        "--all", "-A", help="All backup", dest="all", action="store_true"
    )
    group_export.add_argument(
        "--destination",
        "-d",
        help="Destination path",
        dest="destination",
        action="store",
        required=True,
        metavar="PATH",
    )
    group_export.add_argument(
        "--mirror", "-m", help="Mirror mode", dest="mirror", action="store_true"
    )
    group_export.add_argument(
        "--cut", "-c", help="Cut mode. Delete source", dest="cut", action="store_true"
    )
    group_export.add_argument(
        "--link-folder",
        "-L",
        help="Hard link to other backup folder",
        dest="link",
        metavar="PATH",
    )

    args = parser_object.parse_args()

    # Checks of parser
    if hasattr(args, "retention"):
        if args.retention and len(args.retention) >= 3:
            parser_object.error(
                'The "--retention or -r" parameter must have max two integers. '
                "Three or more arguments specified: {}".format(args.retention),
            )

    # Return all args
    return args


def main():
    """Main process"""

    global args, catalog_path, backup_id, rpath, log_args, logs, hostname, catalog_file

    # Create arguments object
    args = parse_arguments()
    catalog_file = ".catalog.cfg"

    # Check config session
    if args.action == "config":
        if args.new_conf:
            new_configuration()
        elif args.remove_conf:
            remove_configuration()
        elif args.deploy_host:
            deploy_configuration(args.deploy_host, args.deploy_user)
        elif args.init:
            catalog_path = os.path.join(args.init, catalog_file)
            init_catalog(catalog_path)
        elif args.delete:
            catalog_path = os.path.join(args.delete[0], catalog_file)
            delete_host(catalog_path, args.delete[1])
        elif args.delete_backup:
            catalog_path = os.path.join(args.delete_backup[0], catalog_file)
            delete_backup(catalog_path, args.delete_backup[1])
        elif args.clean:
            catalog_path = os.path.join(args.clean, catalog_file)
            clean_catalog(catalog_path)

    # Check backup session
    if args.action == "backup":
        # Check rsync tool
        rsync_path = args.rsync if args.rsync else None
        check_rsync(rsync_path)
        # Check custom ssh port
        port = args.port if args.port else 22
        hostnames = []
        cmds = []
        logs = []
        if args.hostname:
            # Computer list
            hostnames.append(args.hostname)
        elif args.list:
            if os.path.exists(args.list) and os.path.isfile(args.list):
                list_file = open(args.list, "r").read().split()
                for line in list_file:
                    # Computer list
                    hostnames.append(line)
            else:
                utility.error(
                    "The file {0} not exist or is a directory!".format(args.list),
                    nocolor=args.color,
                )
                exit(1)
        for hostname in hostnames:
            ssh_check = utility.check_ssh(hostname, args.user, args.keytype, port)
            if not ssh_check:
                utility.error(
                    "SSH connection failed on {1}:{0}".format(port, hostname),
                    nocolor=args.color,
                )
                continue
            if not args.verbose:
                if not check_configuration(hostname):
                    utility.error(
                        "For bulk or silently backup, deploy configuration! "
                        "See bb config --help or specify --verbose",
                        nocolor=args.color,
                    )
                    continue
            # Log information's
            backup_id = "{}".format(utility.new_id())
            log_args = {
                "id": backup_id,
                "hostname": hostname,
                "status": args.log,
                "destination": os.path.join(args.destination, hostname, "general.log"),
            }
            logs.append(log_args)
            catalog_path = os.path.join(args.destination, catalog_file)
            backup_catalog = read_catalog(catalog_path)
            # Compose command
            cmd = compose_command(args, hostname)
            # Check if start-from is specified
            if args.sfrom:
                if backup_catalog.has_section(args.sfrom):
                    # Check if exist path of backup
                    path = backup_catalog.get(args.sfrom, "path")
                    if os.path.exists(path):
                        cmd.append("--copy-dest={0}".format(path))
                    else:
                        utility.warning(
                            "Backup folder {0} not exist!".format(path),
                            nocolor=args.color,
                        )
                else:
                    utility.error(
                        "Backup id {0} not exist in catalog {1}!".format(
                            args.sfrom, args.destination
                        ),
                        nocolor=args.color,
                    )
                    exit(1)
            utility.print_verbose(
                args.verbose,
                "Create a folder structure for {0} os".format(args.type),
                nocolor=args.color,
            )
            # Write catalog file
            write_catalog(catalog_path, backup_id, "name", hostname)
            write_catalog(catalog_path, backup_id, "os", args.type)
            # Compose source
            source_list = compose_source()
            # Check if hostname is localhost or 127.0.0.1
            if (hostname.lower() == "localhost") or (hostname == "127.0.0.1"):
                # Compose source with only path of folder list
                cmd.append(" ".join(source_list)[1:])
            else:
                # Compose source <user>@<hostname> format
                cmd.append(
                    "{0}@{1}".format(args.user, hostname) + (" ".join(source_list))
                )
            # Compose destination
            bck_dst = compose_destination(hostname, args.destination)
            utility.print_verbose(
                args.verbose,
                "Destination is {0}".format(bck_dst),
                nocolor=args.color,
            )
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "Backup on folder {0}".format(bck_dst),
            )
            cmd.append(bck_dst)
            # Compose pull commands
            cmds.append(" ".join(cmd))
            # Write catalog file
            write_catalog(catalog_path, backup_id, "timestamp", utility.time_for_log())
            # Create a symlink for last backup
            utility.make_symlink(
                bck_dst, os.path.join(args.destination, hostname, "last_backup")
            )
        # Start backup
        if ssh_check:
            if args.wait:
                print("info: wait {} second(s)".format(args.wait))
                time.sleep(args.wait)
            bad_results = run_in_parallel(start_process, cmds, args.parallel)
            # Retry
            if args.retry and bad_results:
                for _ in range(args.retry):
                    utility.warning(
                        "Backup exits with non-zero status; retry backup for {} times".format(
                            args.retry
                        )
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "WARNING",
                        "Backup exits with non-zero status; retry backup for {} times".format(
                            args.retry
                        ),
                    )
                    if args.wait:
                        print("info: wait {} second(s)".format(args.wait))
                        time.sleep(args.wait)
                    bad_results = run_in_parallel(
                        start_process, bad_results, args.parallel
                    )
                    if not bad_results:
                        break
                    args.retry -= 1

    # Check restore session
    if args.action == "restore":
        # Check rsync tool
        rsync_path = args.rsync if args.rsync else None
        check_rsync(rsync_path)
        # Check custom ssh port
        port = args.port if args.port else 22
        cmds = []
        logs = []
        rhost = ""
        hostname = args.hostname
        rpath = ""
        bos = ""
        ros = ""
        rfolders = []
        if not args.type and args.id:
            args.type = get_restore_os()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, catalog_file)
        restore_catalog = read_catalog(catalog_path)
        # Check if select backup-id or last backup
        if args.last:
            rhost = hostname
            last_backup = get_last_backup(restore_catalog)
            if last_backup:
                rpath = last_backup[0]
                if os.path.exists(rpath):
                    if not args.type:
                        args.type = last_backup[1]
                    ros = args.type
                    bos = last_backup[1]
                    if args.files:
                        rfolders = get_files(
                            utility.get_bckid(restore_catalog, last_backup[2]),
                            args.files,
                        )
                    else:
                        rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
                else:
                    utility.error(
                        "Backup folder {0} does not exist!".format(rpath),
                        nocolor=args.color,
                    )
                    exit(1)
            else:
                utility.error(
                    "Last backup {0} does not exist!".format(rpath),
                    nocolor=args.color,
                )
                exit(1)
        elif args.id:
            # Check catalog backup id
            bck_id = utility.get_bckid(restore_catalog, args.id)
            if bck_id:
                # Check if exist path of backup
                if bck_id.get("path") and os.path.exists(bck_id.get("path")):
                    rhost = hostname
                    rpath = bck_id.get("path")
                    bos = bck_id.get("os")
                    ros = args.type
                    if args.files:
                        rfolders = get_files(bck_id, args.files)
                    else:
                        rfolders = [f.path for f in os.scandir(rpath) if f.is_dir()]
                else:
                    utility.error(
                        "Backup folder {0} not exist!".format(bck_id.get("path")),
                        nocolor=args.color,
                    )
                    exit(1)
            else:
                utility.error(
                    "Backup id {0} not exist in catalog {1}!".format(
                        args.id, args.catalog
                    ),
                    nocolor=args.color,
                )
                exit(1)
        # Test connection
        ssh_check = utility.check_ssh(rhost, args.user, args.keytype, port)
        if not ssh_check:
            utility.error(
                "SSH connection failed on {1}:{0}".format(port, rhost),
                nocolor=args.color,
            )
            exit(1)
        if not args.verbose:
            if not check_configuration(rhost):
                utility.error(
                    "For bulk or silently backup to deploy configuration!"
                    "See bb config --help or specify --verbose",
                    nocolor=args.color,
                )
                exit(1)
        log_args = {
            "hostname": rhost,
            "status": args.log,
            "destination": os.path.join(os.path.dirname(rpath), "general.log"),
        }
        utility.write_log(
            log_args["status"],
            log_args["destination"],
            "INFO",
            "Restore on {0}".format(rhost),
        )
        # Check if backup has folder to restore
        if rfolders:
            for rf in rfolders:
                # Append logs
                logs.append(log_args)
                # Compose command
                cmd = compose_command(args, rhost)
                # Compose source and destination
                if args.files:
                    src_dst = compose_restore_src_dst(bos, ros, rf)
                else:
                    src_dst = compose_restore_src_dst(bos, ros, os.path.basename(rf))
                if src_dst:
                    src = src_dst[0]
                    # Compose source
                    cmd.append("'{}'".format(os.path.join(rpath, src)))
                    dst = src_dst[1]
                    if (hostname.lower() == "localhost") or (hostname == "127.0.0.1"):
                        # Compose destination only with path of folder
                        cmd.append("'{}'".format(dst))
                    else:
                        # Compose destination <user>@<hostname> format
                        cmd.append("{0}@{1}:'{2}'".format(args.user, rhost, dst))
                    # Add command
                    if utility.confirm(
                        "info: Want to do restore path {0} into {1} at {2}?".format(
                            os.path.join(rpath, src), rhost, dst
                        ),
                        force=args.force,
                    ):
                        cmds.append(" ".join(cmd))
            # Start restore
            if args.wait:
                print("info: wait {} second(s)".format(args.wait))
                time.sleep(args.wait)
            bad_results = run_in_parallel(start_process, cmds, 1)
            # Retry
            if args.retry and bad_results:
                for _ in range(args.retry):
                    utility.warning(
                        "Backup exits with non-zero status; retry restore for {} times".format(
                            args.retry
                        )
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "WARNING",
                        "Backup exits with non-zero status; retry restore for {} times".format(
                            args.retry
                        ),
                    )
                    if args.wait:
                        print("info: wait {} second(s)".format(args.wait))
                        time.sleep(args.wait)
                    bad_results = run_in_parallel(start_process, bad_results, 1)
                    if not bad_results:
                        break
                    args.retry -= 1
        else:
            utility.warning(
                "Restore files or folders aren't available on backup id {0}".format(
                    args.id if hasattr(args, "id") else args.last
                ),
                nocolor=args.color,
            )

    # Check archive session
    if args.action == "archive":
        # Log info
        log_args = {
            "status": args.log,
            "destination": os.path.join(args.catalog, "archive.log"),
        }
        # Read catalog file
        archive_catalog = os.path.join(args.catalog, catalog_file)
        # Archive paths
        archive_policy(archive_catalog, args.destination)

    # Check list session
    if args.action == "list":
        # Log info
        log_args = {
            "status": args.log,
            "destination": os.path.join(args.catalog, "backup.list"),
        }
        # Read catalog file
        list_catalog = read_catalog(os.path.join(args.catalog, catalog_file))
        # Check specified argument backup-id
        if args.id:
            # Get session backup id
            bck_id = utility.get_bckid(list_catalog, args.id)
            if bck_id:
                if args.ids:
                    print(bck_id.name)
                    exit(0)
                endline = " - " if args.oneline else "\n"
                utility.print_verbose(
                    args.verbose,
                    "Select backup-id: {0}".format(bck_id.name),
                    nocolor=args.color,
                )
                utility.print_values(
                    "Backup id", bck_id.name, nocolor=args.color, endline=endline
                )
                utility.print_values(
                    "Hostname or ip",
                    bck_id.get("name", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Type",
                    bck_id.get("type", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Timestamp",
                    bck_id.get("timestamp", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Start",
                    bck_id.get("start", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Finish",
                    bck_id.get("end", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "OS", bck_id.get("os", ""), nocolor=args.color, endline=endline
                )
                utility.print_values(
                    "ExitCode",
                    bck_id.get("status", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Path",
                    bck_id.get("path", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                if list_catalog.get(args.id, "cleaned", fallback=False):
                    utility.print_values(
                        "Cleaned",
                        bck_id.get("cleaned", "False"),
                        nocolor=args.color,
                        endline=endline,
                    )
                elif list_catalog.get(args.id, "archived", fallback=False):
                    utility.print_values(
                        "Archived",
                        bck_id.get("archived", "False"),
                        nocolor=args.color,
                        endline=endline,
                    )
                else:
                    newline = " " if args.oneline else "\n"
                    if bck_id.get("path"):
                        dirs = os.listdir(bck_id.get("path"))
                    else:
                        dirs = []
                    utility.print_values(
                        "List",
                        "{0}".format(newline).join(dirs),
                        nocolor=args.color,
                    )
            else:
                utility.error(
                    "Backup id {0} doesn't exists".format(args.id),
                    nocolor=args.color,
                )
                exit(1)
        elif args.last:
            bck_id = None
            # Reverse catalog
            list_sections = list_catalog.sections()
            list_sections.reverse()
            for lid in list_sections:
                # Filter for hostname
                if args.hostname:
                    if args.hostname != list_catalog[lid].get("name", ""):
                        continue
                # Get session backup id
                bck_id = list_catalog[lid]
                break
            if bck_id:
                if args.ids:
                    print(bck_id.name)
                    exit(0)
                endline = " - " if args.oneline else "\n"
                utility.print_verbose(
                    args.verbose,
                    "Select backup-id: {0}".format(bck_id.name),
                    nocolor=args.color,
                )
                utility.print_values(
                    "Backup id", bck_id.name, nocolor=args.color, endline=endline
                )
                utility.print_values(
                    "Hostname or ip",
                    bck_id.get("name", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Type",
                    bck_id.get("type", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Timestamp",
                    bck_id.get("timestamp", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Start",
                    bck_id.get("start", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Finish",
                    bck_id.get("end", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "OS", bck_id.get("os", ""), nocolor=args.color, endline=endline
                )
                utility.print_values(
                    "ExitCode",
                    bck_id.get("status", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                utility.print_values(
                    "Path",
                    bck_id.get("path", ""),
                    nocolor=args.color,
                    endline=endline,
                )
                if list_catalog.get(args.id, "cleaned", fallback=False):
                    utility.print_values(
                        "Cleaned",
                        bck_id.get("cleaned", "False"),
                        nocolor=args.color,
                        endline=endline,
                    )
                elif list_catalog.get(args.id, "archived", fallback=False):
                    utility.print_values(
                        "Archived",
                        bck_id.get("archived", "False"),
                        nocolor=args.color,
                        endline=endline,
                    )
                else:
                    newline = " " if args.oneline else "\n"
                    if bck_id.get("path"):
                        dirs = os.listdir(bck_id.get("path"))
                    else:
                        dirs = []
                    utility.print_values(
                        "List",
                        "{0}".format(newline).join(dirs),
                        nocolor=args.color,
                    )
            else:
                utility.warning(
                    "No backup in list",
                    nocolor=args.color,
                )
                exit(0)
        elif args.detail:
            # Get session backup id
            bck_id = utility.get_bckid(list_catalog, args.detail)
            if bck_id:
                log_args["hostname"] = bck_id.get("name")
                logs = [log_args]
                utility.print_verbose(
                    args.verbose,
                    "List detail of backup-id: {0}".format(bck_id.name),
                    nocolor=args.color,
                )
                utility.print_values(
                    "Detail of backup folder",
                    bck_id.get("path", ""),
                    nocolor=args.color,
                )
                if bck_id.get("path") and os.path.exists(bck_id.get("path")):
                    utility.print_values(
                        "List",
                        "\n".join(os.listdir(bck_id.get("path", "-"))),
                        nocolor=args.color,
                    )
                    if log_args["status"]:
                        utility.write_log(
                            log_args["status"],
                            log_args["destination"],
                            "INFO",
                            "BUTTERFLY BACKUP DETAIL (BACKUP-ID: {0} PATH: {1})".format(
                                bck_id.name, bck_id.get("path", "")
                            ),
                        )
                        cmd = "rsync --list-only -r --log-file={0} {1}".format(
                            log_args["destination"], bck_id.get("path")
                        )
                    else:
                        cmd = "rsync --list-only -r {0}".format(bck_id.get("path"))
                else:
                    utility.error(
                        "No such file or directory: {}".format(bck_id.get("path")),
                        nocolor=args.color,
                    )
                    exit(1)
                start_process(cmd)
            else:
                utility.error(
                    "Backup id {0} doesn't exists".format(args.detail),
                    nocolor=args.color,
                )
                exit(1)
        elif args.archived:
            utility.print_verbose(
                args.verbose,
                "List all archived backup in catalog",
                nocolor=args.color,
            )
            text = "BUTTERFLY BACKUP CATALOG (ARCHIVED)\n\n"
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "BUTTERFLY BACKUP CATALOG (ARCHIVED)",
            )
            for lid in list_catalog.sections():
                # Get session backup id
                bck_id = list_catalog[lid]
                if "archived" in bck_id:
                    if args.ids:
                        print(lid)
                        continue
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Backup id: {0}".format(lid),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Hostname or ip: {0}".format(bck_id.get("name", "")),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Timestamp: {0}".format(bck_id.get("timestamp", "")),
                    )
                    text += "Backup id: {0}".format(lid)
                    text += "\n"
                    text += "Hostname or ip: {0}".format(bck_id.get("name", ""))
                    text += "\n"
                    text += "Timestamp: {0}".format(bck_id.get("timestamp", ""))
                    text += "\n\n"
            if not args.ids:
                utility.pager(text)
        elif args.cleaned:
            utility.print_verbose(
                args.verbose,
                "List all cleaned backup in catalog",
                nocolor=args.color,
            )
            text = "BUTTERFLY BACKUP CATALOG (CLEANED)\n\n"
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "BUTTERFLY BACKUP CATALOG (CLEANED)",
            )
            for lid in list_catalog.sections():
                # Get session backup id
                bck_id = list_catalog[lid]
                if "cleaned" in bck_id:
                    if args.ids:
                        print(lid)
                        continue
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Backup id: {0}".format(lid),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Hostname or ip: {0}".format(bck_id.get("name", "")),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Timestamp: {0}".format(bck_id.get("timestamp", "")),
                    )
                    text += "Backup id: {0}".format(lid)
                    text += "\n"
                    text += "Hostname or ip: {0}".format(bck_id.get("name", ""))
                    text += "\n"
                    text += "Timestamp: {0}".format(bck_id.get("timestamp", ""))
                    text += "\n\n"
            if not args.ids:
                utility.pager(text)
        elif args.status is not None:
            utility.print_verbose(
                args.verbose,
                "List all matched status ({}) backup in catalog".format(args.status),
                nocolor=args.color,
            )
            text = "BUTTERFLY BACKUP CATALOG (STATUS={})\n\n".format(args.status)
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "BUTTERFLY BACKUP CATALOG (STATUS={})\n\n".format(args.status),
            )
            for lid in list_catalog.sections():
                # Get session backup id
                bck_id = list_catalog[lid]
                if int(bck_id.get("status", 0)) == args.status:
                    if args.ids:
                        print(lid)
                        continue
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Backup id: {0}".format(lid),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Hostname or ip: {0}".format(bck_id.get("name", "")),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Timestamp: {0}".format(bck_id.get("timestamp", "")),
                    )
                    text += "Backup id: {0}".format(lid)
                    text += "\n"
                    text += "Hostname or ip: {0}".format(bck_id.get("name", ""))
                    text += "\n"
                    text += "Timestamp: {0}".format(bck_id.get("timestamp", ""))
                    text += "\n\n"
            if not args.ids:
                utility.pager(text)
        else:
            utility.print_verbose(
                args.verbose, "List all backup in catalog", nocolor=args.color
            )
            text = "BUTTERFLY BACKUP CATALOG\n\n"
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "BUTTERFLY BACKUP CATALOG",
            )
            if args.hostname:
                for lid in list_catalog.sections():
                    # Get session backup id
                    bck_id = list_catalog[lid]
                    if bck_id.get("name") == args.hostname:
                        if args.ids:
                            print(lid)
                            continue
                        utility.write_log(
                            log_args["status"],
                            log_args["destination"],
                            "INFO",
                            "Backup id: {0}".format(lid),
                        )
                        utility.write_log(
                            log_args["status"],
                            log_args["destination"],
                            "INFO",
                            "Hostname or ip: {0}".format(bck_id.get("name", "")),
                        )
                        utility.write_log(
                            log_args["status"],
                            log_args["destination"],
                            "INFO",
                            "Timestamp: {0}".format(bck_id.get("timestamp", "")),
                        )
                        text += "Backup id: {0}".format(lid)
                        text += "\n"
                        text += "Hostname or ip: {0}".format(bck_id.get("name", ""))
                        text += "\n"
                        text += "Timestamp: {0}".format(bck_id.get("timestamp", ""))
                        text += "\n\n"
            else:
                for lid in list_catalog.sections():
                    if args.ids:
                        print(lid)
                        continue
                    # Get session backup id
                    bck_id = list_catalog[lid]
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Backup id: {0}".format(lid),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Hostname or ip: {0}".format(bck_id.get("name", "")),
                    )
                    utility.write_log(
                        log_args["status"],
                        log_args["destination"],
                        "INFO",
                        "Timestamp: {0}".format(bck_id.get("timestamp", "")),
                    )
                    text += "Backup id: {0}".format(lid)
                    text += "\n"
                    text += "Hostname or ip: {0}".format(bck_id.get("name", ""))
                    text += "\n"
                    text += "Timestamp: {0}".format(bck_id.get("timestamp", ""))
                    text += "\n\n"
            if not args.ids:
                utility.pager(text)

    # Check export session
    if args.action == "export":
        # Check rsync tool
        rsync_path = args.rsync if args.rsync else None
        check_rsync(rsync_path)
        cmds = list()
        # Read catalog file
        catalog_path = os.path.join(args.catalog, catalog_file)
        export_catalog = read_catalog(catalog_path)
        # Create destination folder if not exists
        if not os.path.exists(args.destination):
            utility.make_dir(args.destination)
        # Check one export or all
        if args.all:
            # Log info
            log_args = {
                "hostname": "all_backup",
                "status": args.log,
                "destination": os.path.join(args.destination, "export.log"),
            }
            logs = list()
            logs.append(log_args)
            # Compose command
            cmd = compose_command(args, None)
            # Add source
            cmd.append("{}".format(os.path.join(args.catalog, "")))
            # Add destination
            cmd.append("{}".format(args.destination))
        else:
            # Check specified argument backup-id
            bck_id = utility.get_bckid(export_catalog, args.id)
            if not bck_id:
                utility.error(
                    "Backup-id {0} not exist!".format(args.id), nocolor=args.color
                )
                exit(1)
            # Log info
            log_args = {
                "hostname": bck_id.get("name"),
                "status": args.log,
                "destination": os.path.join(args.destination, "export.log"),
            }
            logs = list()
            logs.append(log_args)
            # Compose command
            cmd = compose_command(args, None)
            # Export
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "INFO",
                "Export {0}. Folder {1} to {2}".format(
                    bck_id.name,
                    bck_id.get("path"),
                    args.destination,
                ),
            )
            utility.print_verbose(
                args.verbose,
                "Export backup with id {0}".format(bck_id.name),
                nocolor=args.color,
            )
            if bck_id.get("path") and os.path.exists(bck_id.get("path")):
                # Add source
                cmd.append("{}".format(bck_id.get("path")))
                # Add destination
                cmd.append(
                    "{}".format(
                        os.path.join(
                            args.destination,
                            bck_id.get("name"),
                        )
                    )
                )
                utility.write_log(
                    log_args["status"],
                    log_args["destination"],
                    "INFO",
                    "Export command {0}.".format(" ".join(cmd)),
                )
                # Check cut option
                if args.cut:
                    write_catalog(
                        os.path.join(args.catalog, catalog_file),
                        args.id,
                        "cleaned",
                        "True",
                    )
        # Start export
        if args.wait:
            print("info: wait {} second(s)".format(args.wait))
            time.sleep(args.wait)
        cmds.append(" ".join(cmd))
        bad_results = run_in_parallel(start_process, cmds, 1)
        # Retry
        if args.retry and bad_results:
            for _ in range(args.retry):
                utility.warning(
                    "Backup exits with non-zero status; retry export for {} times".format(
                        args.retry
                    )
                )
                utility.write_log(
                    log_args["status"],
                    log_args["destination"],
                    "WARNING",
                    "Backup exits with non-zero status; retry export for {} times".format(
                        args.retry
                    ),
                )
                if args.wait:
                    print("info: wait {} second(s)".format(args.wait))
                    time.sleep(args.wait)
                bad_results = run_in_parallel(start_process, bad_results, 1)
                if not bad_results:
                    break
                args.retry -= 1
        # Migrate catalog to new file system
        if os.path.exists(os.path.join(args.destination, catalog_file)):
            utility.find_replace(
                os.path.join(args.destination, catalog_file),
                args.catalog.rstrip("/"),
                args.destination.rstrip("/"),
            )


if __name__ == "__main__":
    global args, catalog_path, backup_id, rpath, log_args, logs, hostname
    try:
        main()
    except Exception as err:
        if "log_args" in globals():
            utility.write_log(
                log_args["status"],
                log_args["destination"],
                "CRITICAL",
                "Something wrong: {0}.".format(err),
            )
        utility.report_issue(err, args.error)
