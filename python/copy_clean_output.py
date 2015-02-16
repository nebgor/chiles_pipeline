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
import fnmatch
import multiprocessing
import os
from os.path import join, isdir, basename
import sys
import datetime

from common import make_safe_filename, Consumer, make_tarfile, LOGGER
from copy_cvel_output import CopyTask
from settings_file import CHILES_BUCKET_NAME, CHILES_CLEAN_OUTPUT, CHILES_LOGS
from s3_helper import S3Helper

LOGGER.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(self, output_tar_filename, frequency_id, directory_to_save):
        self._output_tar_filename = output_tar_filename
        self._frequency_id = frequency_id
        self._directory_to_save = directory_to_save

    def __call__(self):
        """
        Actually run the job
        """
        # noinspection PyBroadException
        try:
            make_tarfile(self._output_tar_filename, self._directory_to_save)

            LOGGER.info('Copying {0} to s3'.format(self._output_tar_filename))
            s3_helper = S3Helper()
            s3_helper.add_file_to_bucket_multipart(
                CHILES_BUCKET_NAME,
                '/CLEAN/{0}/{1}'.format(self._frequency_id, basename(self._output_tar_filename)),
                self._output_tar_filename)

            # Clean up
            os.remove(self._output_tar_filename)
        except Exception:
            LOGGER.exception('Task died')


def copy_files(frequency_id, processes):
    # Create the queue
    queue = multiprocessing.JoinableQueue()
    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()

    # Look in the output directory
    directory_data = join(CHILES_CLEAN_OUTPUT, frequency_id)
    LOGGER.info('directory_data: {0}'.format(directory_data))
    for dir_name in os.listdir(directory_data):
        LOGGER.info('dir_name: {0}'.format(dir_name))
        if isdir(join(directory_data, dir_name)) and dir_name.startswith('cube_'):
            LOGGER.info('dir_name: {0}'.format(dir_name))
            output_tar_filename = join(directory_data, dir_name + '.tar.gz')
            queue.put(Task(output_tar_filename, frequency_id, join(directory_data, dir_name)))

    for root, dir_names, filenames in os.walk(CHILES_LOGS):
        for match in fnmatch.filter(filenames, '*.log'):
            LOGGER.info('Looking at: {0}'.format(join(root, match)))
            queue.put(CopyTask(join(root, match), 'CLEAN-logs/{0}/{1}/log/{2}'.format(frequency_id, root, match)))

    today = datetime.date.today()
    queue.put(CopyTask('/var/log/chiles-output.log', 'CLEAN-logs/{0}/{1}{2}{3}/chiles-output.log'.format(frequency_id, today.year, today.month, today.day)))

    # Add a poison pill to shut things down
    for x in range(processes):
        queue.put(None)

    # Wait for the queue to terminate
    queue.join()


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output to the correct place in S3')
    parser.add_argument('frequency_id', help='the frequency id')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    args = vars(parser.parse_args())
    frequency_id = args['frequency_id']
    processes = args['processes']

    copy_files(frequency_id, processes)

if __name__ == "__main__":
    main()
