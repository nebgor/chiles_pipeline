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
import fnmatch
import multiprocessing
import os
from os.path import join
import sys

from common import make_safe_filename, Consumer, make_tarfile, LOGGER
from settings_file import CHILES_CVEL_OUTPUT, CHILES_BUCKET_NAME
from s3_helper import S3Helper


LOGGER.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(self, output_tar_filename, frequency_band, date, directory_frequency_full):
        self._output_tar_filename = output_tar_filename
        self._frequency_band = frequency_band
        self._date = date
        self._directory_frequency_full = directory_frequency_full

    def __call__(self):
        """
        Actually run the job
        """
        # noinspection PyBroadException
        try:
            make_tarfile(self._output_tar_filename, self._directory_frequency_full)

            LOGGER.info('Copying {0} to s3'.format(self._output_tar_filename))
            s3_helper = S3Helper()
            s3_helper.add_file_to_bucket(
                CHILES_BUCKET_NAME,
                'CVEL/{0}/{1}/data.tar.gz'.format(self._frequency_band, self._date),
                self._output_tar_filename)

            # Clean up
            os.remove(self._output_tar_filename)
        except Exception:
            LOGGER.exception('Task died')


def copy_files(date, processes):
    # Create the queue
    queue = multiprocessing.JoinableQueue()
    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()
    s3_helper = S3Helper()

    # Look in the output directory
    for root, dir_names, filenames in os.walk(CHILES_CVEL_OUTPUT):
        for match in fnmatch.filter(dir_names, 'vis_*'):
            result_dir = join(root, match)
            LOGGER.info('Looking at: {0}'.format(result_dir))

            output_tar_filename = join(root, match + '.tar.gz')
            queue.put(Task(output_tar_filename, match, date, result_dir))

            s3_helper.add_file_to_bucket(
                CHILES_BUCKET_NAME,
                'CVEL-logs/{0}/{1}/log/chiles-output.log'.format(date, match),
                '/var/log/chiles-output.log')
    # s3_helper.add_file_to_bucket(
    #    CHILES_BUCKET_NAME,
    #    observation_id + '/CVEL/' + directory_day + '/log/casapy.log',
    #    join('/home/ec2-user/Chiles/casa_work_dir/{0}-0/casapy.log'.format(directory_day)))

    # Add a poison pill to shut things down
    for x in range(processes):
        queue.put(None)

    # Wait for the queue to terminate
    queue.join()


def main():
    parser = argparse.ArgumentParser('Copy the CVEL output to the correct place in S3')
    parser.add_argument('date', help='the date of the observation')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    args = vars(parser.parse_args())
    date = make_safe_filename(args['date'])
    processes = args['processes']

    copy_files(date, processes)

if __name__ == "__main__":
    main()
