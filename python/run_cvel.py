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
Start a number of CVEL servers
"""
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import getpass
import multiprocessing
import sys

from common import make_safe_filename, get_cloud_init, setup_boto, get_script, Consumer
from config import AWS_AMI_ID, BASH_SCRIPT_CVEL
from ec2_helper import EC2Helper


LOG = multiprocessing.log_to_stderr(multiprocessing.SUBDEBUG)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(self, ec2_helper, ami_id, user_data, instance_type, observation_id, volume_id, created_by, name, spot_price):
        self._ec2_helper = ec2_helper
        self._ami_id = ami_id
        self._user_data = user_data
        self._instance_type = instance_type
        self._observation_id = observation_id
        self._volume_id = volume_id
        self._created_by = created_by
        self._name = name
        self._spot_price = spot_price

    def __call__(self):
        """
        Actually run the job
        """
        # Get the name of the volume
        volume_name = self._ec2_helper.get_volume_name(self._volume_id)
        LOG.info('observation_id: {0}, volume_name: {1}'.format(self._observation_id, volume_name))
        user_data_mime = get_mime_encoded_user_data(self._user_data, volume_name, self._observation_id)

        if self._spot_price is not None:
            ec2_instance = self._ec2_helper.run_spot_instance(
                self._ami_id,
                self._spot_price,
                user_data_mime,
                self._instance_type,
                self._volume_id,
                self._created_by,
                self._name + '- {0}'.format(volume_name),
                ephemeral=True)
        else:
            ec2_instance = self._ec2_helper.run_instance(
                self._ami_id,
                user_data_mime,
                self._instance_type,
                self._volume_id,
                self._created_by,
                self._name + '- {0}'.format(volume_name),
                ephemeral=True)

        # Setup boto via SSH so we don't pass our keys etc in "the clear"
        setup_boto(ec2_instance.ip_address)


def start_servers(processes, ami_id, user_data, instance_type, observation_id, volume_ids, created_by, name, spot_price=None):
    # Create the queue
    tasks = multiprocessing.JoinableQueue()

    # Start the consumers
    for x in range(processes):
        consumer = Consumer(tasks)
        consumer.start()

    ec2_helper = EC2Helper()
    for volume_id in volume_ids:
        tasks.put(Task(ec2_helper, ami_id, user_data, instance_type, observation_id, volume_id, created_by, name, spot_price))

        # Add a poison pill to shut things down
    for x in range(processes):
        tasks.put(None)

    # Wait for the queue to terminate
    tasks.join()


def get_mime_encoded_user_data(data, volume_name, observation_id):
    """
    AWS allows for a multipart m
    """
    user_data = MIMEMultipart()

    user_data.attach(get_cloud_init())

    data_formatted = data.format(volume_name, observation_id)
    user_data.attach(MIMEText(data_formatted))
    return user_data.as_string()


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}

    if args['obs_id'] is None:
        return None

    if args['vol_ids'] is None:
        return None

    if args['instance_type'] is None:
        return None

    if args['name'] is None:
        return None

    map_args.update({
        'ami_id': args['ami_id'] if args['ami_id'] is not None else AWS_AMI_ID,
        'created_by': args['created_by'] if args['created_by'] is not None else getpass.getuser(),
        'spot_price': args['spot_price'] if args['spot_price'] is not None else None,
        'user_data': get_script(args['bash_script'] if args['bash_script'] is not None else BASH_SCRIPT_CVEL)})

    return map_args


def main():
    parser = argparse.ArgumentParser('Start a number of CVEL servers')
    parser.add_argument('-a', '--ami_id', help='the AMI id to use')
    parser.add_argument('-i', '--instance_type', required=True, help='the instance type to use')
    parser.add_argument('-c', '--created_by', help='the username to use')
    parser.add_argument('-n', '--name', required=True, help='the instance name to use')
    parser.add_argument('-s', '--spot_price', type=float, help='the spot price to use')
    parser.add_argument('-b', '--bash_script', help='the bash script to use')
    parser.add_argument('-p', '--processes', type=int, default=1, help='the number of processes to run')
    parser.add_argument('obs_id', help='the observation id')
    parser.add_argument('vol_ids', nargs='+', help='the volume ids to use')

    args = vars(parser.parse_args())

    corrected_args = check_args(args)
    if corrected_args is None:
        LOG.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(
            args['processes'],
            corrected_args['ami_id'],
            corrected_args['user_data'],
            args['instance_type'],
            make_safe_filename(args['obs_id']),
            args['vol_ids'],
            corrected_args['created_by'],
            args['name'],
            corrected_args['spot_price'])

if __name__ == "__main__":
    # -i r3.xlarge -n "Kevin cvel test" -s 0.10 obs-1 vol-f7dda9f3 vol-22deaa26 vol-70c2b674 vol-66c2b662
    main()
