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
Copy the CVEL output files to S3
"""
import argparse
import logging
import os
from os.path import isdir, join
import sys
import tarfile
from common import make_safe_filename
from config import CHILES_CVEL_OUTPUT, CHILES_BUCKET_NAME
from s3_helper import S3Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def make_tarfile(output_filename, source_dir):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))


def main():
    parser = argparse.ArgumentParser('Copy the output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])

    s3_helper = S3Helper()
    # Look in the output directory
    for directory_day in os.listdir(CHILES_CVEL_OUTPUT):
        if isdir(join(CHILES_CVEL_OUTPUT, directory_day)):
            path_frequency = join(CHILES_CVEL_OUTPUT, directory_day, 'data1')
            for directory_frequency in os.listdir(path_frequency):
                directory_frequency_full = join(path_frequency, directory_frequency)
                if directory_frequency.startswith('vis_') and isdir(directory_frequency_full):
                    output_tar_filename = join(path_frequency, directory_frequency + '.tar.gz')
                    make_tarfile(output_tar_filename, directory_frequency_full)
                    s3_helper.add_file_to_bucket(CHILES_BUCKET_NAME, observation_id + '/' + directory_frequency + '/' + directory_day + '/data.tar.gz', output_tar_filename)

        s3_helper.add_file_to_bucket(CHILES_BUCKET_NAME, observation_id + '/' + directory_day + '/logs/chiles-output.log', '/var/logs/chiles-output.log')
        s3_helper.add_file_to_bucket(CHILES_BUCKET_NAME, observation_id + '/' + directory_day + '/logs/casapy.log', join('/home/ec2-user/Chiles/casa_work_dir/{0}-0'.format(directory_day)))

if __name__ == "__main__":
    main()
