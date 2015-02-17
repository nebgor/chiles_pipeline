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
Copy the CLEAN output from S3
"""
import argparse
from contextlib import closing
import multiprocessing
import os
from os.path import basename, exists
import sys
import tarfile

from common import LOGGER, Consumer
from settings_file import CHILES_BUCKET_NAME
from s3_helper import S3Helper


LOGGER.info('PYTHONPATH = {0}'.format(sys.path))
DIRECTORY = '/mnt/output/Chiles/'


class Task(object):
    """
    The actual task
    """
    def __init__(self, key, tar_file, directory):
        self._key = key
        self._tar_file = tar_file
        self._directory = directory

    def __call__(self):
        """
        Actually run the job
        """
        # noinspection PyBroadException
        try:
            LOGGER.info('key: {0}, tar_file: {1}, directory: {2}'.format(self._key.key, self._tar_file, self._directory))
            if not os.path.exists(self._directory):
                os.makedirs(self._directory)
            self._key.get_contents_to_filename(self._tar_file)
            with closing(tarfile.open(self._tar_file, "r:gz")) as tar:
                tar.extractall(path=self._directory)

            os.remove(self._tar_file)
        except Exception:
            LOGGER.exception('Task died')


def copy_files(processes):
    # Create the directory
    if not exists(DIRECTORY):
        os.makedirs(DIRECTORY)

    # Scan the bucket
    s3_helper = S3Helper()
    bucket = s3_helper.get_bucket(CHILES_BUCKET_NAME)
    LOGGER.info('Scanning bucket: {0}/CLEAN'.format(bucket))

    # Create the queue
    queue = multiprocessing.JoinableQueue()

    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()

    for key in bucket.list(prefix='CLEAN'):
        LOGGER.info('Checking {0}'.format(key.key))
        # Ignore the key
        if key.key.endswith('.image.tar.gz'):
            # Queue the copy of the file
            temp_file = os.path.join(DIRECTORY, basename(key.key))
            queue.put(Task(key, temp_file, DIRECTORY))

    # Add a poison pill to shut things down
    for x in range(processes):
        queue.put(None)

    # Wait for the queue to terminate
    queue.join()


def main():
    parser = argparse.ArgumentParser('Copy the CLEAN output from S3')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')

    args = vars(parser.parse_args())
    processes = args['processes']

    copy_files(processes)

if __name__ == "__main__":
    main()
