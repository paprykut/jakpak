#!/usr/bin/env python3

"""
Description: Retrieve package info from Arch Rollback Machine as of a given
             date and compare the differences with your local packages.
Author: Mikołaj Romel
License: MIT
(C) 2014
"""

from sys import maxsize
from shlex import split
from requests import get
from termcolor import cprint, colored
from datetime import datetime
from bs4 import BeautifulSoup
from sys import exit as errexit
from subprocess import Popen, PIPE
from argparse import ArgumentParser, ArgumentTypeError


def _get_arch():
    """
    Find user's cpu arch.
    """

    # If True = x86_64.
    if maxsize > 2 ** 32:
        arch = 'x86_64'
    else:
        arch = 'i686'

    return arch


def _parse_cmdline():
    """
    Parse the command line arguments.
    """

    parser = ArgumentParser()
    parser.add_argument('-d', '--date',
                        help='Give the exact date that you want to check \
                              for packages. Format: DD-MM-YYYY',
                        required=True, type=_validate_date)

    parser.add_argument('-r', '--repository',
                        help='Give specific repository to compare [community, \
                        community-staging, community-testing, core, extra, \
                        gnome-unstable, kde-unstable, multilib, \
                        multilib-staging, multilib-testing, pool, staging, \
                        testing, lastsync, lastupdate]',
                        required=True, type=str)

    cmdline_args = parser.parse_args()
    return cmdline_args


def _local_packages(repo):
    """
    Build the list of local packages. Use `pacman -Q`.
    """

    # Get the list of local packages in a repo spcified by the user.
    cmd = "paclist %s" % repo
    proc = Popen(split(cmd), stdout=PIPE)
    out, err = proc.communicate()

    # Del, so pyflakes does not complain.
    del err

    # Popen() returns a byte string. Decode it to split() on it.
    # Split and cut off the last empty line.
    # Also, use some formatting to put it in line with the output of
    # _repo_packages().
    pkg_list = out.decode().replace(' ', '-').split('\n')[:-1]

    # Loop over in order to do some final formatting. Append to local_pkgs.
    local_pkgs = []

    for pkg in pkg_list:
        local_pkgs.append(pkg.split('-'))

    return local_pkgs


def _repo_packages(arch, cmdline_args):
    """
    Return the repo packages at given day.
    """

    # Base http address of the rollback machine.
    http_addr = 'http://seblu.net/a/arm/'

    # Reformat the date string supplied by the user.
    date = cmdline_args.date.split('-')

    # Get specific repo.
    repo = cmdline_args.repository

    # Construct http address. Blah.
    # date[0] is day, date[1] is month, date[2] is year.
    http = http_addr + '/' + '/' + \
        date[2] + '/' + date[1] + '/' + date[0] + '/' + \
        repo + '/' + '/' + 'os' + '/' + arch

    request = get(http)

    # Exit if could not retrieve the data. Most probably the user provided
    # wrong data.
    if request.status_code == 404:
        exitmsg = colored('Wrong values provided. Check whether the date ' +
                          'and the repository are correct!\n', attrs=['bold'])

        errexit(exitmsg)

    # Get the initial list of packages. Remove tags by bs4.
    soup = BeautifulSoup(request.content)

    # Format the repo packages accordingly. First, create a list to which those
    # packages will be appended.
    repo_pkg_list = []

    # Get rid of the signatures, so only the real packages stay on the list
    # (if the file ends with '.sig', it is not a package). Also, when
    # appending, remove the '-*.pkg.tar.gz*' part using regex.
    for pkg in soup.find_all('a'):
        pkg_add = pkg.get('href')
        if not pkg_add.endswith('.sig'):
            # Append. Replace '%3a' with ':'. Also, replace '%2b' to '+'.
            repo_pkg_list.append(pkg_add.
                                 replace('%3a', ':').
                                 replace('%2b', '+').
                                 split('-')[:-1])

    # Return the list without the first element as it is empty.
    return repo_pkg_list[1:]


def _validate_date(date_string):
    """
    Validate whether the command line date provided by the user really is in a
    date format DD-MM-YYYY.
    """

    try:
        if datetime.strptime(date_string, '%d-%m-%Y'):
            return date_string
    except ValueError:
        raise ArgumentTypeError("invalid date format: '%s'. " % date_string +
                                "Please use the format of: DD-MM-YYYY.")


def _compare_pkgs(local_pkgs, repo_pkgs):
    """
    Compare the local and repo packages and show differences.
    """

    # The most burdensome stuff now. The names of the packages are split now,
    # thus they might look like:
    # ['acl', '2.5.52', '2'] for acl, but also like:
    # ['procps', 'ng', '3.3.9', '2'] for propcs-ng (spot the lack of a dash).
    # Not relevant now, but perhaps might get relevant in the future.

    # Keep differences.
    pkg_diff = []

    # Loop. If pkg is in repo (full name + version), it means no changes.
    # Otherwise, the package was upgraded since the specified date.
    for local_pkg in local_pkgs:
        if not local_pkg in repo_pkgs:
            # Not in remote repo? It means changes. Thus, another loop to find
            # the version from the repo and append both: local_pkg and
            # repo_pkg to pkg_diff.
            # While looping, compare local_pkg and repo_pkg without the
            # versions, just the package names.
            for repo_pkg in repo_pkgs:
                if local_pkg[:-2] == repo_pkg[:-2]:
                    pkg_diff.append({'local': local_pkg, 'repo': repo_pkg})

    return pkg_diff


def _output_diff(diff_pkgs):
    """
    Output formatted information about the changes in packages to stdout.
    """

    # Format output.
    for diff_pkg in diff_pkgs:
        # Name of the package.
        cprint('-'.join(diff_pkg['local'][:-2]).ljust(30),
               'magenta', attrs=['bold'], end=' ')

        # 'local version' string.
        cprint('local version: ', attrs=['bold'], end='')

        # Local version.
        cprint('-'.join(diff_pkg['local'][-2:]).ljust(25),
               'green', attrs=['bold'], end='')

        # 'repo version' string..
        cprint('repo version: ', attrs=['bold'], end='')

        # Repo version.
        cprint('-'.join(diff_pkg['repo'][-2:]).ljust(25),
               'red', attrs=['bold'])


def _run():
    """
    Run all of the above in a relevant order.
    """

    # Get config.
    arch = _get_arch()

    # Parse command line arguments.
    cmdline_args = _parse_cmdline()

    # Get the list of local packages in a given repo.
    local_pkgs = _local_packages(cmdline_args.repository)

    # Get the list of packages in a repo on a given date.
    repo_pkgs = _repo_packages(arch, cmdline_args)

    # Finally, compare the local and repo packages.
    diff_pkgs = _compare_pkgs(local_pkgs, repo_pkgs)

    # And output them to stdout.
    _output_diff(diff_pkgs)

if __name__ == '__main__':
    _run()
