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
from contextlib import closing
from glob import glob
import logging
import multiprocessing
from os.path import join, isdir, basename
import sys
import tarfile

from common import make_safe_filename
from config import CHILES_BUCKET_NAME, CHILES_CLEAN_OUTPUT
from s3_helper import S3Helper

if multiprocessing.current_process().name == "MainProcess":
    LOG = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
else:
    LOG = multiprocessing.get_logger()
    LOG.setLevel(multiprocessing.SUBDEBUG)

LOG.info('PYTHONPATH = {0}'.format(sys.path))


def make_tarfile(directory_data, frequency_id):
    output_filename = join(directory_data, frequency_id + '.tar.gz')
    LOG.info('directory_data: {0}, frequency_id: {1}, output_filename: {2}'.format(directory_data, frequency_id, output_filename))
    with closing(tarfile.open(output_filename, "w:gz")) as tar:
        for dir_name in glob('{0}/*'.format(directory_data)):
            if isdir(dir_name) and basename(dir_name).startswith('cube_'):
                tar.add(dir_name, arcname=basename(dir_name))

    return output_filename


def copy_files(observation_id, frequency_id):
    # Create the
    s3_helper = S3Helper()

    # Look in the output directory
    directory_data = join(CHILES_CLEAN_OUTPUT, observation_id)
    LOG.info('directory_data: {0}'.format(directory_data))
    tar_filename = make_tarfile(directory_data, frequency_id)
    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/CLEAN/' + frequency_id + '/data.tar.gz',
        tar_filename)

    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/CLEAN/' + frequency_id + '/log/chiles-output.log',
        '/var/log/chiles-output.log')
    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/CLEAN/' + frequency_id + '/log/casapy.log',
        join('/mnt/output/Chiles/casa_work_dir/{0}-0/casapy.log'.format(observation_id)))


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('frequency_id', help='the frequency id')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])
    frequency_id = args['frequency_id']

    copy_files(observation_id, frequency_id)

if __name__ == "__main__":
    main()
