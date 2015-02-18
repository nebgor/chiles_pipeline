#
#    (c) UWA, The University of Western Australia
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA, 2012-2015
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

from common import get_cloud_init, setup_aws_machine, get_script, Consumer, LOGGER
from echo import dump_all
from settings_file import AWS_AMI_ID, BASH_SCRIPT_CVEL, FREQUENCY_GROUPS, OBS_IDS, AWS_INSTANCES, BASH_SCRIPT_SETUP_DISKS
from ec2_helper import EC2Helper


LOGGER.info('PYTHONPATH = {0}'.format(sys.path))


class Task(object):
    """
    The actual task
    """
    def __init__(
            self,
            ami_id,
            user_data,
            setup_disks,
            instance_type,
            obs_id,
            snapshot_id,
            created_by,
            name,
            spot_price,
            zone,
            instance_details,
            frequency_groups,
            counter):
        self._ami_id = ami_id
        self._user_data = user_data
        self._setup_disks = setup_disks
        self._instance_type = instance_type
        self._obs_id = obs_id
        self._snapshot_id = snapshot_id
        self._created_by = created_by
        self._name = name
        self._spot_price = spot_price
        self._zone = zone
        self._instance_details = instance_details
        self._frequency_groups = frequency_groups
        self._counter = counter

    def __call__(self):
        """
        Actually run the job
        """
        # Get the name of the volume
        ec2_helper = EC2Helper()
        volume, snapshot_name = ec2_helper.create_volume(self._snapshot_id, self._zone)
        LOGGER.info('obs_id: {0}, volume_name: {1}'.format(self._obs_id, snapshot_name))
        user_data_mime = self.get_mime_encoded_user_data(self._user_data, volume.id)

        if self._spot_price is not None:
            ec2_instance = ec2_helper.run_spot_instance(
                self._ami_id,
                self._spot_price,
                user_data_mime,
                self._instance_type,
                volume.id,
                self._created_by,
                '{2}-{0}-{1}'.format(self._name, snapshot_name, self._counter),
                ephemeral=True)
        else:
            ec2_instance = ec2_helper.run_instance(
                self._ami_id,
                user_data_mime,
                self._instance_type,
                volume.id,
                self._created_by,
                '{2}-{0}-{1}'.format(self._name, snapshot_name, self._counter),
                ephemeral=True)

        # Setup boto via SSH so we don't pass our keys etc in "the clear"
        setup_aws_machine(ec2_instance.ip_address)

    def get_mime_encoded_user_data(self, data, volume_id):
        """
        AWS allows for a multipart m
        """
        user_data = MIMEMultipart()
        user_data.attach(get_cloud_init())

        # Build the strings we need
        cvel_pipeline = self.build_cvel_pipeline()

        data_formatted = data.format(cvel_pipeline, self._obs_id, volume_id)
        LOGGER.info(data_formatted)
        user_data.attach(MIMEText(data_formatted))
        return user_data.as_string()

    def build_cvel_pipeline(self):
        return_string = ''
        for frequnecy_pairs in self._frequency_groups:
            return_string += '''
runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_cvel.sh {0} {1}'
'''.format(frequnecy_pairs[0], frequnecy_pairs[1])

        return return_string


def get_frequency_groups(pairs_per_group):
    """
    >>> get_frequency_groups(1)
    [[[1400, 1404]], [[1404, 1408]], [[1408, 1412]], [[1412, 1416]], [[1416, 1420]], [[1420, 1424]]]
    >>> get_frequency_groups(2)
    [[[1400, 1404], [1404, 1408]], [[1408, 1412], [1412, 1416]], [[1416, 1420], [1420, 1424]]]
    >>> get_frequency_groups(3)
    [[[1400, 1404], [1404, 1408], [1408, 1412]], [[1412, 1416], [1416, 1420], [1420, 1424]]]
    """
    frequency_groups = []
    frequency_group = []
    counter = 0
    for frequency_pair in FREQUENCY_GROUPS:
        frequency_group.append(frequency_pair)
        counter += 1
        if counter == pairs_per_group:
            frequency_groups.append(frequency_group)
            counter = 0
            frequency_group = []

    if len(frequency_group) > 0:
        frequency_groups.append(frequency_group)

    return frequency_groups


def start_servers(
        processes,
        ami_id,
        user_data,
        setup_disks,
        instance_type,
        obs_ids,
        created_by,
        name,
        instance_details,
        spot_price,
        zone):
    # Create the queue
    tasks = multiprocessing.JoinableQueue()

    # Start the consumers
    for x in range(processes):
        consumer = Consumer(tasks)
        consumer.start()

    counter = 1
    for obs_id in obs_ids:
        snapshot_id = OBS_IDS.get(obs_id)
        if snapshot_id is None:
            LOGGER.warning('The obs-id: {0} does not exist in the settings file')
        else:
            for frequency_groups in get_frequency_groups(6):
                tasks.put(
                    Task(
                        ami_id,
                        user_data,
                        setup_disks,
                        instance_type,
                        obs_id,
                        snapshot_id,
                        created_by,
                        name,
                        spot_price,
                        zone,
                        instance_details,
                        frequency_groups,
                        counter))
                counter += 1

        # Add a poison pill to shut things down
    for x in range(processes):
        tasks.put(None)

    # Wait for the queue to terminate
    tasks.join()


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}

    if args['obs_ids'] is None:
        return None
    elif len(args['obs_ids']) == 1 and args['obs_ids'][0] == '*':
        map_args['obs_ids'] = OBS_IDS.keys()
    else:
        map_args['obs_ids'] = args['obs_ids']

    if args['instance_type'] is None:
        return None

    if args['name'] is None:
        return None

    instance_details = AWS_INSTANCES.get(args['instance_type'])
    if instance_details is None:
        LOGGER.error('The instance type {0} is not supported.'.format(args['instance_type']))
        return None
    else:
        LOGGER.info(
            'instance: {0}, vCPU: {1}, RAM: {2}GB, Disks: {3}x{4}GB'.format(
                args['instance_type'],
                instance_details[0],
                instance_details[1],
                instance_details[2],
                instance_details[3]))

    map_args.update({
        'ami_id': args['ami_id'] if args['ami_id'] is not None else AWS_AMI_ID,
        'created_by': args['created_by'] if args['created_by'] is not None else getpass.getuser(),
        'spot_price': args['spot_price'] if args['spot_price'] is not None else None,
        'user_data': get_script(args['bash_script'] if args['bash_script'] is not None else BASH_SCRIPT_CVEL),
        'setup_disks': get_script(BASH_SCRIPT_SETUP_DISKS),
        'instance_details': instance_details,
    })

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

    parser.add_argument('obs_ids', nargs='+', help='the ids of the observation')

    args = vars(parser.parse_args())

    corrected_args = check_args(args)
    if corrected_args is None:
        LOGGER.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(
            args['processes'],
            corrected_args['ami_id'],
            corrected_args['user_data'],
            corrected_args['setup_disks'],
            args['instance_type'],
            corrected_args['obs_ids'],
            corrected_args['created_by'],
            args['name'],
            corrected_args['instance_details'],
            corrected_args['spot_price'],
            'ap-southeast-2a')

if __name__ == "__main__":
    # -i r3.xlarge -n "Kevin cvel test" -s 0.10 20131025_951_4 20131031_951_4
    main()
