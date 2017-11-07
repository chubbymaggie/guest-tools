#!/usr/bin/env python

# Copyright (C) 2017, Adrian Herrera
# All rights reserved.
#
# Licensed under the MIT License.

"""
Extracts the Windows kernel executable (``ntoskrnl.exe``) from an ISO. This is
useful when updating the ``winmonitor_gen.c`` file, as the kernel executable
is used to generate the correct data structure offsets for that particular
kernel.

Usage
-----

::

    python extract_kernels.py -d /path/to/isos -o /path/to/output

Where ``isos`` is a directory containing all or some of the supported ISOs
listed in s2e/guest-images/images.json and ``output`` is the directory to store
the kernel executable files.

Requirements
------------

Requires 7-Zip (http://www.7-zip.org/) and that the ``7z`` executable is
available on the ``PATH``.

This script will work with both Python 2.7 and 3.x.
"""


from __future__ import print_function


import argparse
import os
import shutil
import subprocess

try:
    from subprocess import DEVNULL
except ImportError:
    DEVNULL = open(os.devnull, 'wb')

import sys
import tempfile


# Maps Windows ISOs (taken from the supported images listed in
# s2e/guest-images/images.json) to the location of ntoskrnl.exe within the ISO.
#
# ntoskrnl.exe is stored within an intermediary container. The path to this
# intermediary container is given in the first element in the value tuple. The
# second tuple element is the path to ntoskrnl.exe within this intermediary
# container.
NTOSKRNL_MAP = {
    'en_windows_xp_professional_with_service_pack_3_x86_cd_x14-80428.iso':
        (os.path.join('I386', 'NTOSKRNL.EX_'),
         'ntoskrnl.exe'),
    'en_windows_7_enterprise_with_sp1_x64_dvd_u_677651.iso':
        (os.path.join('sources', 'install.wim'),
         os.path.join('Windows', 'System32', 'ntoskrnl.exe')),
    'en_windows_8_1_enterprise_x64_dvd_2971902.iso':
        (os.path.join('sources', 'install.wim'),
         os.path.join('Windows', 'System32', 'ntoskrnl.exe')),
    'en_windows_10_enterprise_version_1703_updated_march_2017_x64_dvd_10189290.iso':
        (os.path.join('sources', 'install.wim'),
         os.path.join('Windows', 'System32', 'ntoskrnl.exe')),
}


# Adapted from http://stackoverflow.com/a/19299884/5894531
class TemporaryDirectory(object):
    """
    Create and return a temporary directory.  This has the same behavior as
    mkdtemp but can be used as a context manager. For example:

        with TemporaryDirectory() as tmpdir:
            ...

    Upon exiting the context, the directory and everything contained in it are
    removed.
    """

    def __init__(self, suffix='', prefix='tmp', dir_=None):
        self._closed = False
        self.name = None
        self.name = tempfile.mkdtemp(suffix, prefix, dir_)

    def __repr__(self):
        return '<{} {!r}>'.format(self.__class__.__name__, self.name)

    def __enter__(self):
        return self.name

    def __exit__(self, exc, value, tb):
        self.cleanup()

    def __del__(self):
        self.cleanup(warn=True)

    def cleanup(self, warn=False):
        if self.name and not self._closed:
            try:
                shutil.rmtree(self.name)
            except Exception as e:
                print('ERROR: {!r} while cleaning up {!r}'.format(e, self),
                      file=sys.stderr)
                return

            self._closed = True
            if warn:
                print('Implicitly cleaning up {!r}'.format(self))


def parse_args():
    """Parse the command-line arguments."""
    parser = argparse.ArgumentParser(description='Extract Windows kernels.')
    parser.add_argument('-d', '--iso-dir', required=True,
                        help='Path to the directory containing the ISOs')
    parser.add_argument('-o', '--output-dir', default=os.getcwd(),
                        help='Directory to store the extract kernels. '
                             'Defaults to the current working directory')

    return parser.parse_args()


def seven_zip_extract(source, files, dest=None):
    """
    Execute 7zip and extract the list of `files` from the `source` archive.
    """
    if not dest:
        dest = os.getcwd()

    args = ['7z', 'e', source]
    args.extend(files)

    proc = subprocess.Popen(args, stdout=DEVNULL, stderr=subprocess.PIPE,
                            cwd=dest)
    _, stderr = proc.communicate()

    return proc.returncode, stderr


def main():
    """The main function."""
    args = parse_args()

    iso_dir = args.iso_dir
    if not os.path.isdir(iso_dir):
        raise Exception('%s is not a valid ISO directory' % iso_dir)

    output_dir = args.output_dir
    if not os.path.isdir(output_dir):
        raise Exception('%s is not a valid output directory' % output_dir)

    iso_dir = os.path.realpath(iso_dir)
    output_dir = os.path.realpath(output_dir)

    for iso, (container, krnl) in NTOSKRNL_MAP.items():
        iso_path = os.path.join(iso_dir, iso)
        if not os.path.isfile(iso_path):
            print(u'[\u2717] %s does not exist. Skipping...' % iso)
            continue

        with TemporaryDirectory() as temp_dir:
            print('[-] Extracting ntoskrnl.exe from %s...' % iso)

            # Extract the kernel container
            returncode, stderr = seven_zip_extract(iso_path, [container],
                                                   temp_dir)
            if stderr:
                print(u'[\u2717] Failed to extract %s from %s: "%s"' %
                      (container, iso, stderr))
                continue

            _, container_name = os.path.split(container)
            container_path = os.path.join(temp_dir, container_name)

            # Extract the kernel executable
            returncode, stderr = seven_zip_extract(container_path, [krnl],
                                                   temp_dir)
            if returncode:
                print(u'[\u2717] Failed to extract ntoskrnl.exe from %s: "%s"' %
                      (container_name, stderr))
                continue

            # Rename the kernel executable (they are all called ntoskrnl.exe!)
            # and move it to the output directory
            iso_name, _ = os.path.splitext(iso)
            shutil.move(os.path.join(temp_dir, 'ntoskrnl.exe'),
                        os.path.join(output_dir, '%s_ntoskrnl.exe' % iso_name))

        print(u'[\u2713] Successfully extracted ntoskrnl.exe from %s' % iso)


if __name__ == '__main__':
    main()
