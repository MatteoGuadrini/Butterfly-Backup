#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: se ts=4 et syn=python:

# created by: matteo.guadrini
# utility.py -- Butterfly-Backup
#
#     Copyright (C) 2023 Matteo Guadrini <matteo.guadrini@hotmail.it>
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
from pansi import ansi


def get_bckid(catalog, bckid):
    """Get backup id from catalog"""
    # Check if bckid is 8 char
    if len(bckid) == 8:
        for ids in catalog.sections():
            if bckid == ids[:8]:
                return catalog[ids]
    # Get bckid, if exists
    if catalog.has_section(bckid):
        return catalog[bckid]


def report_issue(exc):
    """Report issue"""
    error(
        "{0} on line {1}, with error '{2}'".format(
            type(exc).__name__, exc.__traceback__.tb_lineno, str(exc)
        )
    )
    exit(1)


def warning(message):
    """Print warning message in yellow color

    :param message: message to print
    """
    print("{ansi.yellow}warning: {0}{ansi.reset}".format(message, ansi=ansi))


def error(message):
    """Print error message in red color

    :param message: message to print
    """
    print("{ansi.red}error: {0}{ansi.reset}".format(message, ansi=ansi))


def success(message):
    """Print success message in green color

    :param message: message to print
    """
    print("{ansi.green}success: {0}{ansi.reset}".format(message, ansi=ansi))


def print_values(key, value, endline="\n"):
    """Print key/value in cyan color

    :param key: key to print
    :param value: value to print
    :param endline: endline value
    """
    print(key + ":", "{ansi.cyan}{0}{ansi.reset}".format(value, ansi=ansi), end=endline)


def touch(filename, times=None):
    """
    Create an empty file
    :param filename: path of file
    :param times: time creation of file
    :return:  file
    """
    import os

    # Verify folder exists
    if not os.path.exists(filename):
        # touch file
        with open(filename, "a"):
            os.utime(filename, times)


def find_replace(filename, text_to_search, replacement_text):
    """
    Find and replace word in a text file
    :param filename: path of file
    :param text_to_search: word to search
    :param replacement_text: word to replace
    :return:  file
    """
    import fileinput

    with fileinput.FileInput(filename, inplace=True) as file:
        for line in file:
            print(line.replace(text_to_search, replacement_text), end="")


def write_log(status, log, level, message):
    """
    Write custom log in a custom path
    :param status: if True, log to file
    :param log: path of log file
    :param level: level of log message
    :param message: message of log
    """
    # Check if status is True
    if status:
        import logging
        import getpass

        # Create logging object
        f_o_r_m_a_t = logging.Formatter(
            "%(asctime)s %(name)-4s %(levelname)-4s %(message)s"
        )
        handler = logging.FileHandler(log)
        handler.setFormatter(f_o_r_m_a_t)
        logger = logging.getLogger(getpass.getuser())
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Check log level
        if level == "INFO":
            logger.info(message)
        elif level == "WARNING":
            logger.warning(message)
        elif level == "ERROR":
            logger.error(message)
        elif level == "CRITICAL":
            logger.critical(message)

        # Remove handler
        logger.removeHandler(handler)


def make_dir(directory):
    """
    Create a folder
    :param directory: Path of folder
    """
    import os

    if not os.path.exists(directory):
        os.makedirs(directory)


def time_for_folder():
    """
    Time now() in this format: %Y_%m_%d__%H_%M
    :return: string time
    """
    import time

    return time.strftime("%Y_%m_%d__%H_%M")


def time_for_log():
    """
    Time now() in this format: %Y-%m-%d %H:%M:%S
    :return: string time
    """
    import time

    return time.strftime("%Y-%m-%d %H:%M:%S")


def cleanup(path, date, days):
    """
    Delete folder to pass an first argument, when time of it is minor of certain date
    :param path: path to delete
    :param date: date passed of path
    :param days: number of days
    :return:
    """
    from shutil import rmtree
    from time import mktime
    from datetime import datetime, timedelta

    d = datetime.today() - timedelta(days=days)
    seconds = mktime(d.timetuple())
    date_s = mktime(string_to_time(date).timetuple())
    if date_s < seconds:
        try:
            rmtree(path)
            exitcode = 0
            return exitcode
        except OSError:
            exitcode = 1
            return exitcode


def new_id():
    """
    Generate new uuid
    :return: uuid object
    """
    import uuid

    return uuid.uuid1()


def string_to_time(string):
    """
    Convert time string into date object in this format '%Y-%m-%d %H:%M:%S'
    :param string: Time format string
    :return: time object
    """
    from datetime import datetime

    datetime_object = datetime.strptime(string, "%Y-%m-%d %H:%M:%S")
    return datetime_object


def time_to_string(date):
    """
    Convert date into string object in this format '%Y-%m-%d %H:%M:%S'
    :param date: Date object
    :return: string
    """
    from datetime import datetime

    string = datetime.strftime(date, "%Y-%m-%d %H:%M:%S")
    return string


def make_symlink(source, destination):
    """
    Make a symbolic link
    :param source: Source path of symbolic link
    :param destination: Destination path of symbolic link
    """
    import os

    try:
        if os.path.exists(destination):
            os.unlink(destination)
        os.symlink(source, destination)
    except OSError:
        warning("MS-DOS file system doesn't support symlink file")


def list_from_string(string):
    """
    Cast string in list
    :param string: Input string must be transform in list
    :return: list
    """
    # Convert string to list separated with comma
    return_list = string.split(",")
    return return_list


def confirm(message, default="n"):
    """
    Ask user to enter Y or N (case-insensitive).
    :message: message to print
    :default: default answer
    :return: True if the answer is Y.
    :rtype: bool
    """
    answer = ""
    while answer not in ["y", "n"]:
        answer = input(
            "{0}\nTo continue? {1}".format(
                message, "[Y/n]" if default == "y" else "[y/N]"
            )
        ).lower()
        # Check if default
        if not answer:
            answer = default
            break
    return answer == "y"


def print_verbose(verbose_status, *messages):
    """
    Print verbose information
    :return: Verbose message if verbose status is True
    :rtype: str
    """
    if verbose_status:
        print(
            "{ansi.white}debug:".format(ansi=ansi),
            *messages,
            "{ansi.reset}".format(ansi=ansi),
        )


def check_tool(name):
    """
    Check tool is installed
    :param name: name of the tool
    :return: boolean
    """
    from shutil import which

    return which(name) is not None


def check_ssh(ip, port=22):
    """
    Test ssh connection
    :param ip: ip address or hostname of machine
    :param port: ssh port (default is 22)
    """
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, port))
        s.shutdown(2)
        return True
    except socket.error:
        return False


def archive(path, date, days, destination):
    """
    Archive entire folder in a zip file
    :param path: path than would archive in a zip file
    :param date: date passed of path
    :param days: number of days
    :param destination: destination of zip file
    :return: boolean
    """
    import shutil
    import os
    from time import mktime
    from datetime import datetime, timedelta

    d = datetime.today() - timedelta(days=days)
    seconds = mktime(d.timetuple())
    date_s = mktime(string_to_time(date).timetuple())
    if date_s < seconds:
        if os.path.exists(path):
            if os.path.exists(destination):
                try:
                    archive_from = os.path.dirname(path)
                    archive_to = os.path.basename(path.strip(os.sep))
                    final_dest = os.path.join(
                        destination, os.path.basename(os.path.dirname(path))
                    )
                    if not os.path.exists(final_dest):
                        os.mkdir(final_dest)
                    os.chdir(final_dest)
                    name = os.path.basename(path)
                    shutil.make_archive(name, "zip", archive_from, archive_to)
                    exitcode = 0
                    clean = cleanup(path, date, days)
                    if clean == 0:
                        success("Delete {0} successfully.".format(path))
                    elif clean != 0:
                        error("Delete {0} failed.".format(path))
                    return exitcode
                except OSError:
                    exitcode = 1
                    return exitcode
            else:
                error("The destination path {0} is not exist.".format(destination))
        else:
            error("The path {0} is not exist.".format(path))


def pager(text):
    """
    Pagination function like less
    :param text: text than would see with pagination
    :return: docstring
    """
    import pydoc

    pydoc.pager(text)
