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
import multiprocessing
import os
from os.path import join, isdir, basename
import sys

from common import make_safe_filename, Consumer, make_tarfile
from config import CHILES_BUCKET_NAME, CHILES_CLEAN_OUTPUT
from s3_helper import S3Helper

LOG = multiprocessing.log_to_stderr(multiprocessing.SUBDEBUG)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(self, s3_helper, output_tar_filename, observation_id, frequency_id, directory_to_save):
        self._s3_helper = s3_helper
        self._output_tar_filename = output_tar_filename
        self._observation_id = observation_id
        self._frequency_id = frequency_id
        self._directory_to_save = directory_to_save

    def __call__(self):
        """
        Actually run the job
        """
        try:
            make_tarfile(self._output_tar_filename, self._directory_to_save)

            LOG.info('Copying {0} to s3'.format(self._output_tar_filename))
            self._s3_helper.add_file_to_bucket(
                CHILES_BUCKET_NAME,
                self._observation_id + '/CLEAN/' + self._frequency_id + '/' + basename(self._output_tar_filename) + '.tar.gz',
                self._output_tar_filename)

            # Clean up
            os.remove(self._output_tar_filename)
        except:
            LOG.exception('Task died')


def copy_files(observation_id, frequency_id, processes):
    # Create the queue
    queue = multiprocessing.JoinableQueue()
    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()

    # Create the helper
    s3_helper = S3Helper()

    # Look in the output directory
    directory_data = join(CHILES_CLEAN_OUTPUT, observation_id)
    LOG.info('directory_data: {0}'.format(directory_data))
    for dir_name in os.listdir(directory_data):
        LOG.info('dir_name: {0}'.format(dir_name))
        if isdir(join(directory_data, dir_name)) and dir_name.startswith('cube_'):
            LOG.info('dir_name: {0}'.format(dir_name))
            output_tar_filename = join(directory_data, dir_name + '.tar.gz')
            queue.put(Task(s3_helper, output_tar_filename, observation_id, frequency_id, join(directory_data, dir_name)))

    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/CLEAN/' + frequency_id + '/log/chiles-output.log',
        '/var/log/chiles-output.log')
    s3_helper.add_file_to_bucket(
        CHILES_BUCKET_NAME,
        observation_id + '/CLEAN/' + frequency_id + '/log/casapy.log',
        join('/mnt/output/Chiles/casa_work_dir/{0}-0/casapy.log'.format(observation_id)))

    # Add a poison pill to shut things down
    for x in range(processes):
        queue.put(None)

    # Wait for the queue to terminate
    queue.join()


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('frequency_id', help='the frequency id')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])
    frequency_id = args['frequency_id']
    processes = args['processes']

    copy_files(observation_id, frequency_id, processes)

if __name__ == "__main__":
    main()
