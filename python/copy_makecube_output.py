#
#    (c) UWA, The University of Western Australia
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA, 2012-2014
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
Copy the clean output
"""
import argparse
import os
from os.path import join, isdir, basename
import sys

from common import make_safe_filename, Consumer, make_tarfile, LOGGER
from config import CHILES_BUCKET_NAME, CHILES_IMGCONCAT_OUTPUT
from s3_helper import S3Helper

LOGGER.info('PYTHONPATH = {0}'.format(sys.path))


def copy_files(observation_id, processes):
    # Create the helper
    s3_helper = S3Helper()

    # Look in the output directory
    directory_to_save = join(CHILES_IMGCONCAT_OUTPUT, observation_id) + '.cube'
    if isdir(directory_to_save):
        LOGGER.info('dir_name: {0}'.format(directory_to_save))
        output_tar_filename = directory_to_save + '.tar.gz'
        try:
            make_tarfile(output_tar_filename, directory_to_save)

            LOGGER.info('Copying {0} to s3'.format(output_tar_filename))
            s3_helper = S3Helper()
            s3_helper.add_file_to_bucket_multipart(
                CHILES_BUCKET_NAME,
                observation_id + '/IMGCONCAT/' + basename(output_tar_filename),
                output_tar_filename)

            # Clean up
            os.remove(output_tar_filename)
        except Exception:
            LOGGER.exception('Task died')

    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/IMGCONCAT/log/chiles-output.log',
        '/var/log/chiles-output.log')
    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/IMGCONCAT/log/casapy.log',
        join('/mnt/output/Chiles/casa_work_dir/casapy.log'.format(observation_id)))


def main():
    parser = argparse.ArgumentParser('Copy the IMGCONCAT output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])
    processes = args['processes']

    copy_files(observation_id, processes)

if __name__ == "__main__":
    main()
