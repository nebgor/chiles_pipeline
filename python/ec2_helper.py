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
The helper for starting EC2 Instances
"""
import time
import datetime

import boto
from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.exception import EC2ResponseError
from boto.ec2 import blockdevicemapping

from common import make_safe_filename, LOGGER
from settings_file import AWS_SUBNET_ID, AWS_KEY_NAME, AWS_SECURITY_GROUPS, AWS_REGION


class EC2Helper:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None):
        """
        Get an EC2 connection
        """
        if aws_access_key_id is not None and aws_secret_access_key is not None:
            self.ec2_connection = boto.ec2.connect_to_region(AWS_REGION, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        else:
            # This relies on a ~/.boto file holding the '<aws access key>', '<aws secret key>'
            self.ec2_connection = boto.ec2.connect_to_region(AWS_REGION)

    @staticmethod
    def build_block_device_map(ephemeral, number_ephemeral_disks=1, ebs_size=None):
        bdm = blockdevicemapping.BlockDeviceMapping()

        if ephemeral:
            # The ephemeral disk
            xvdb = BlockDeviceType()
            xvdb.ephemeral_name = 'ephemeral0'
            bdm['/dev/xvdb'] = xvdb

            if number_ephemeral_disks == 2:
                xvdc = BlockDeviceType()
                xvdc.ephemeral_name = 'ephemeral1'
                bdm['/dev/xvdc'] = xvdc

        if ebs_size:
            xvdc = blockdevicemapping.EBSBlockDeviceType(delete_on_termination=True)
            xvdc.size = int(ebs_size)  # size in Gigabytes
            bdm['/dev/xvdc'] = xvdc

        return bdm

    def run_instance(self, ami_id, user_data, instance_type, volume_id, created_by, name, ephemeral=False):
        """
        Run up an instance
        """
        bdm = self.build_block_device_map(ephemeral)

        LOGGER.info('Running instance: ami: {0}'.format(ami_id))
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
            LOGGER.info('Not running yet')
            time.sleep(5)

        if volume_id:
            # Now we have an instance id we can attach the disk
            self.ec2_connection.attach_volume(volume_id, instance.id, '/dev/xvdf')

        LOGGER.info('Assigning the tags')
        self.ec2_connection.create_tags([instance.id],
                                        {'AMI': '{0}'.format(ami_id),
                                         'Name': '{0}'.format(name),
                                         'Volume_id': '{0}'.format(volume_id),
                                         'Created By': '{0}'.format(created_by)})

        return instance

    def run_spot_instance(self, ami_id, spot_price, user_data, instance_type, volume_id, created_by, name, instance_details, ephemeral=False):
        """
        Run the ami as a spot instance
        """
        now_plus = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
        bdm = self.build_block_device_map(ephemeral, instance_details.number_disks)
        spot_request = self.ec2_connection.request_spot_instances(
            spot_price,
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
                LOGGER.exception('Error count = {0}'.format(error_count))
                error_count += 1

            if requests is None:
                # Wait for AWS to catch up
                time.sleep(10)
            else:
                LOGGER.info('{0}, state: {1}, status:{2}'.format(spot_request_id, requests[0].state, requests[0].status))
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

        LOGGER.info('Waiting to start up')
        while not instance.update() == 'running':
            LOGGER.info('Not running yet')
            time.sleep(5)

        if volume_id:
            LOGGER.info('Attaching {0}'.format(volume_id))
            # When we have an instance id we can attach the volume
            self.ec2_connection.attach_volume(volume_id, instance_id, '/dev/xvdf')

        # Give it time to settle down
        LOGGER.info('Assigning the tags')
        self.ec2_connection.create_tags(
            [instance_id],
            {
                'AMI': '{0}'.format(ami_id),
                'Name': '{0}'.format(name),
                'Volume_id': '{0}'.format(volume_id),
                'Created By': '{0}'.format(created_by)
            })

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

    def create_volume(self, snapshot_id, zone, iops=None):
        snapshot = self.ec2_connection.get_all_snapshots([snapshot_id])
        volume = self.ec2_connection.create_volume(None, zone, snapshot=snapshot_id, volume_type='gp2', iops=iops)
        snapshot_name = snapshot[0].tags['Name']

        self.ec2_connection.create_tags(volume.id, {'Name': 'CAN BE DELETED: ' + snapshot_name})

        return volume, snapshot_name

    def delete_volume(self, volume_id):
        volume = self.ec2_connection.get_all_volumes([volume_id])[0]
        LOGGER.info('status = {0}'.format(volume.status))
        if volume.status == 'in-use':
            # Unattach
            volume.detach()

            for i in range(0, 10):
                time.sleep(5)

                volume = self.ec2_connection.get_all_volumes([volume_id])[0]
                LOGGER.info('status = {0}'.format(volume.status))
                if volume.status == 'available':
                    break

        volume = self.ec2_connection.get_all_volumes([volume_id])[0]
        LOGGER.info('status = {0}'.format(volume.status))
        if volume.status == 'available':
            self.ec2_connection.delete_volume(volume_id)


class CancelledException(Exception):
    """
    The request has been cancelled
    """
    pass
