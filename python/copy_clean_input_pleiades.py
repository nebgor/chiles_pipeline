#
#    (c) UWA, The University of Western Australia
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA, 2012-2015
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
"""
Copy the CVEL output from S3 so we can run clean on it
"""
import argparse
from contextlib import closing
import logging
import os
from os.path import join
import shutil
import sys
import tarfile
from pleiades_common import get_expect_combinations

from settings_file import CHILES_BUCKET_NAME
from s3_helper import S3Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)

LOG.info('PYTHONPATH = {0}'.format(sys.path))
DIRECTORY = '/mnt/hidata/kevin/split_vis'


def copy_files(frequency_id):
    s3_helper = S3Helper()
    bucket = s3_helper.get_bucket(CHILES_BUCKET_NAME)
    LOG.info('Scanning bucket: {0}, frequency_id: {1}'.format(bucket, frequency_id))

    for key in bucket.list(prefix='CVEL/{0}'.format(frequency_id)):
        LOG.info('Checking {0}'.format(key.key))
        # Ignore the key
        if key.key.endswith('/data.tar.gz') or key.key.endswith('/data.tar'):
            elements = key.key.split('/')
            directory = '{1}/{0}/'.format(elements[2], DIRECTORY)

            # Queue the copy of the file
            tar_file = os.path.join(directory, 'data.tar.gz' if key.key.endswith('/data.tar.gz') else 'data.tar')
            corrected_path = join(directory, frequency_id)
            # noinspection PyBroadException
            try:
                LOG.info('key: {0}, tar_file: {1}, directory: {2}, frequency_id: {3}'.format(
                    key.key,
                    tar_file,
                    directory,
                    frequency_id))
                if os.path.exists(corrected_path):
                    LOG.info('Corrected_path already exists: {0}'.format(corrected_path))
                else:
                    os.makedirs(corrected_path)
                    key.get_contents_to_filename(tar_file)
                    with closing(tarfile.open(tar_file, "r:gz" if tar_file.endswith('tar.gz') else "r:")) as tar:
                        tar.extractall(path=corrected_path)

                    os.remove(tar_file)
            except Exception:
                LOG.exception('Task died')
                shutil.rmtree(corrected_path, ignore_errors=True)


def command_pbs(args):
    # The id is the array id
    array_id = args.array_id

    expected_combinations = get_expect_combinations()
    copy_files(expected_combinations[array_id])


def command_list(args):
    LOG.info('{0}'.format(args))
    expected_combinations = get_expect_combinations()
    count = 0
    for combination in expected_combinations:
        LOG.info('{0} - {1}'.format(count, combination))
        count += 1


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output from S3')
    subparsers = parser.add_subparsers()

    parser_pbs = subparsers.add_parser('pbs', help='pbs help')
    parser_pbs.add_argument('array_id', type=int, help='the array id from the PDS job')
    parser_pbs.set_defaults(func=command_pbs)

    parser_galaxy = subparsers.add_parser('list', help='list help')
    parser_galaxy.set_defaults(func=command_list)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
