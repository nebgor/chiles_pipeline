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
Copy the CVEL output from S3 so we can run clean on it
"""
import argparse
import logging
import sys
import os
import tarfile
from common import make_safe_filename
from config import CHILES_BUCKET_NAME
from s3_helper import S3Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def copy_files(observation_id, frequency_id):
    s3_helper = S3Helper()
    bucket = s3_helper.get_bucket(CHILES_BUCKET_NAME)

    for key in bucket.list(prefix='{0}/{1}'.format(observation_id, frequency_id)):
        # Ignore the key
        if key.key.endswith('/data.tar.gz'):
            elements = key.key.split('/')
            directory = '/mnt/output/Chiles/split_vis/{0}/data1/{1}'.format(elements[2], frequency_id)
            if not os.path.exists(directory):
                os.makedirs(directory)

            # Copy the file over
            temp_file = os.path.join(directory, 'data.tar.gz')
            key.get_contents_to_filename(temp_file)
            with tarfile.open(temp_file, "r:gz") as tar:
                tar.extractall(path=directory)

            #os.remove(temp_file)


def main():
    parser = argparse.ArgumentParser('Copy the output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('freq_id', help='the frequency id')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])
    frequency_id = args['freq_id']

    copy_files(observation_id, frequency_id)

if __name__ == "__main__":
    main()
