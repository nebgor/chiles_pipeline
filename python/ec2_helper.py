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
The helper for starting EC2 Instances
"""
import multiprocessing
import logging
import time
import datetime

import boto
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.exception import EC2ResponseError
from boto.ec2 import blockdevicemapping

from common import make_safe_filename
from config import AWS_SUBNET_ID, AWS_KEY_NAME, AWS_SECURITY_GROUPS, AWS_REGION


LOG = multiprocessing.log_to_stderr()
LOG.setLevel(logging.INFO)


class EC2Helper:
    def __init__(self):
        """
        Get an EC2 connection
        """
        # This relies on a ~/.boto file holding the '<aws access key>', '<aws secret key>'
        self.ec2_connection = boto.ec2.connect_to_region(AWS_REGION)

    @staticmethod
    def build_block_device_map(ephemeral):
        bdm = blockdevicemapping.BlockDeviceMapping()

        if ephemeral:
            # The ephemeral disk
            xvdb = BlockDeviceType()
            xvdb.ephemeral_name = 'ephemeral0'
            bdm['/dev/xvdb'] = xvdb

        return bdm

    def run_instance(self, ami_id, user_data, instance_type, volume_id, created_by, name, ephemeral=False):
        """
        Run up an instance
        """
        bdm = self.build_block_device_map(ephemeral)

        LOG.info('Running instance: ami: {0}'.format(ami_id))
        reservations = self.ec2_connection.run_instances(ami_id,
                                                         instance_type=instance_type,
                                                         instance_initiated_shutdown_behavior='terminate',
                                                         subnet_id=AWS_SUBNET_ID,
                                                         key_name=AWS_KEY_NAME,
                                                         security_group_ids=AWS_SECURITY_GROUPS,
                                                         user_data=user_data,
                                                         block_device_map=bdm)
        instance = reservations.instances[0]
        time.sleep(5)

        while not instance.update() == 'running':
            LOG.info('Not running yet')
            time.sleep(5)

        if volume_id:
            # Now we have an instance id we can attach the disk
            self.ec2_connection.attach_volume(volume_id, instance.id, '/dev/xvdf')

        LOG.info('Assigning the tags')
        self.ec2_connection.create_tags([instance.id],
                                        {'CVEL': '{0}'.format(ami_id),
                                         'Name': '{0}'.format(name),
                                         'Volume_id': '{0}'.format(volume_id),
                                         'Created By': '{0}'.format(created_by)})

        return instance

    def run_spot_instance(self, ami_id, spot_price, user_data, instance_type, volume_id, created_by, name, ephemeral=False):
        """
        Run the ami as a spot instance
        """
        now_plus = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        bdm = self.build_block_device_map(ephemeral)
        spot_request = self.ec2_connection.request_spot_instances(spot_price,
                                                                  image_id=ami_id,
                                                                  count=1,
                                                                  valid_until=now_plus.isoformat(),
                                                                  instance_type=instance_type,
                                                                  subnet_id=AWS_SUBNET_ID,
                                                                  key_name=AWS_KEY_NAME,
                                                                  security_group_ids=AWS_SECURITY_GROUPS,
                                                                  user_data=user_data,
                                                                  block_device_map=bdm)

        # Wait for EC2 to provision the instance
        time.sleep(10)
        instance_id = None
        error_count = 0

        # Has it been provisioned yet - we allow 3 errors before aborting
        while instance_id is None and error_count < 3:
            spot_request_id = spot_request[0].id
            requests = None
            try:
                requests = self.ec2_connection.get_all_spot_instance_requests(request_ids=[spot_request_id])
            except EC2ResponseError:
                LOG.exception('Error count = {0}'.format(error_count))
                error_count += 1

            if requests is None:
                # Wait for AWS to catch up
                time.sleep(10)
            else:
                LOG.info('{0}, state: {1}, status:{2}'.format(spot_request_id, requests[0].state, requests[0].status))
                if requests[0].state == 'active' and requests[0].status.code == 'fulfilled':
                    instance_id = requests[0].instance_id
                elif requests[0].state == 'cancelled':
                    raise CancelledException('Request {0} cancelled. Status: {1}'.format(spot_request_id, requests[0].status))
                elif requests[0].state == 'failed':
                    raise CancelledException('Request {0} failed. Status: {1}. Fault: {2}'.format(spot_request_id, requests[0].status, requests[0].fault))
                else:
                    time.sleep(10)

        reservations = self.ec2_connection.get_all_instances(instance_ids=[instance_id])
        instance = reservations[0].instances[0]

        LOG.info('Waiting to start up')
        while not instance.update() == 'running':
            LOG.info('Not running yet')
            time.sleep(5)

        if volume_id:
            # When we have an instance id we can attach the volume
            self.ec2_connection.attach_volume(volume_id, instance_id, '/dev/xvdf')

        # Give it time to settle down
        LOG.info('Assigning the tags')
        self.ec2_connection.create_tags([instance_id],
                                        {'CVEL': '{0}'.format(ami_id),
                                         'Name': '{0}'.format(name),
                                         'Volume_id': '{0}'.format(volume_id),
                                         'Created By': '{0}'.format(created_by)})

        return instance

    def get_volume_name(self, volume_id):
        """
        Get the name of volume (if it has one)
        """
        volume_details = self.ec2_connection.get_all_volumes(volume_id)
        if volume_details and len(volume_details) == 1:
            volume = volume_details[0]
            name = volume.tags['Name']
            if name:
                return make_safe_filename(name)

        return volume_id


class CancelledException(Exception):
    """
    The request has been cancelled
    """
    pass
