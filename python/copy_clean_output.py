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
from os.path import join, isdir
import sys

from common import make_safe_filename, Consumer
from config import CHILES_BUCKET_NAME, CHILES_CLEAN_OUTPUT
from s3_helper import S3Helper

LOG = multiprocessing.log_to_stderr()
LOG.setLevel(multiprocessing.SUBDEBUG)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def copy_files(observation_id, processes):
    # Create the queue
    queue = multiprocessing.JoinableQueue()
    # Start the consumers
    for x in range(processes):
        consumer = Consumer(queue)
        consumer.start()
    s3_helper = S3Helper()

    # Look in the output directory
    for directory_day in os.listdir(CHILES_CLEAN_OUTPUT):
        if isdir(join(CHILES_CLEAN_OUTPUT, directory_day)):
            path_frequency = join(CHILES_CLEAN_OUTPUT, directory_day, 'data1')
            LOG.info('path_frequency: {0}'.format(path_frequency))
            # TODO

        s3_helper.add_file_to_bucket(
            CHILES_BUCKET_NAME,
            observation_id + '/CLEAN/' + directory_day + '/log/chiles-output.log',
            '/var/log/chiles-output.log')
        s3_helper.add_file_to_bucket(
            CHILES_BUCKET_NAME,
            observation_id + '/CLEAN/' + directory_day + '/log/casapy.log',
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
