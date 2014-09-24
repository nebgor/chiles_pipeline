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
from contextlib import closing
import logging
import multiprocessing
import os
from os.path import isdir, join
import sys
import tarfile

from common import make_safe_filename, Consumer, make_tarfile
from config import CHILES_CVEL_OUTPUT, CHILES_BUCKET_NAME
from s3_helper import S3Helper


if multiprocessing.current_process().name == "MainProcess":
    LOG = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
else:
    LOG = multiprocessing.get_logger()
    LOG.setLevel(multiprocessing.SUBDEBUG)

LOG.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(self, s3_helper, output_tar_filename, directory_frequency_full, observation_id, directory_frequency, directory_day):
        self._s3_helper = s3_helper
        self._output_tar_filename = output_tar_filename
        self._directory_frequency_full = directory_frequency_full
        self._observation_id = observation_id
        self._directory_frequency = directory_frequency
        self._directory_day = directory_day

    def __call__(self):
        """
        Actually run the job
        """
        try:
            make_tarfile(self._output_tar_filename, self._directory_frequency_full)

            LOG.info('Copying {0} to s3'.format(self._output_tar_filename))
            self._s3_helper.add_file_to_bucket(
                CHILES_BUCKET_NAME,
                self._observation_id + '/CVEL/' + self._directory_frequency + '/' + self._directory_day + '/data.tar.gz',
                self._output_tar_filename)

            # Clean up
            os.remove(self._output_tar_filename)
        except:
            LOG.exception('Task died')


def copy_files(observation_id, processes):
    # Create the queue
    queue = multiprocessing.JoinableQueue()
    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()
    s3_helper = S3Helper()

    # Look in the output directory
    for directory_day in os.listdir(CHILES_CVEL_OUTPUT):
        if isdir(join(CHILES_CVEL_OUTPUT, directory_day)):
            path_frequency = join(CHILES_CVEL_OUTPUT, directory_day, 'data1')
            LOG.info('path_frequency: {0}'.format(path_frequency))
            for directory_frequency in os.listdir(path_frequency):
                directory_frequency_full = join(path_frequency, directory_frequency)
                if directory_frequency.startswith('vis_') and isdir(directory_frequency_full):
                    LOG.info('directory_frequency: {0}, directory_frequency_full: {1}'.format(directory_frequency, directory_frequency_full))
                    output_tar_filename = join(path_frequency, directory_frequency + '.tar.gz')
                    queue.put(Task(s3_helper, output_tar_filename, directory_frequency_full, observation_id, directory_frequency, directory_day))

        s3_helper.add_file_to_bucket(
            CHILES_BUCKET_NAME,
            observation_id + '/CVEL/' + directory_day + '/log/chiles-output.log',
            '/var/log/chiles-output.log')
        s3_helper.add_file_to_bucket(
            CHILES_BUCKET_NAME,
            observation_id + '/CVEL/' + directory_day + '/log/casapy.log',
            join('/home/ec2-user/Chiles/casa_work_dir/{0}-0/casapy.log'.format(directory_day)))

    # Add a poison pill to shut things down
    for x in range(processes):
        queue.put(None)

    # Wait for the queue to terminate
    queue.join()


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output to the correct place in S3')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    args = vars(parser.parse_args())
    observation_id = make_safe_filename(args['obs_id'])
    processes = args['processes']

    copy_files(observation_id, processes)

if __name__ == "__main__":
    main()
