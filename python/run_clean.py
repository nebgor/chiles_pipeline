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
import logging
import sys
from common import get_script, setup_boto, get_cloud_init
from config import AWS_AMI_ID, BASH_SCRIPT_CLEAN
from ec2_helper import EC2Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def start_servers(ami_id, user_data, instance_type, observation_id, frequency_ids, created_by, name, spot_price=None):
    ec2_helper = EC2Helper()
    count = 1
    for frequency_id in frequency_ids:
        # Get the name of the volume
        user_data_mime = get_mime_encoded_user_data(user_data, observation_id, frequency_id)

        if spot_price is not None:
            ec2_instance = ec2_helper.run_spot_instance(ami_id, spot_price, user_data_mime, instance_type, None, created_by, name + '- {0}'.format(frequency_id), ephemeral=True)
        else:
            ec2_instance = ec2_helper.run_instance(ami_id, user_data_mime, instance_type, None, created_by, name + '- {0}'.format(frequency_id), ephemeral=True)

        # Setup boto via SSH so we don't pass our keys etc in "the clear"
        setup_boto(ec2_instance.ip_address)

        count += 1


def get_mime_encoded_user_data(data, observation_id, frequency_id):
    """
    AWS allows for a multipart m
    """
    user_data = MIMEMultipart()

    user_data.attach(get_cloud_init())

    data_formatted = data.format(observation_id, frequency_id)
    user_data.attach(MIMEText(data_formatted))
    return user_data.as_string()


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}

    if args['obs_id'] is not None:
        map_args['obs_id'] = args['obs_id']
    else:
        return None

    if args['frequencies'] is not None:
        map_args['frequencies'] = args['frequencies']
    else:
        return None

    if args['instance_type'] is not None:
        map_args['instance_type'] = args['instance_type']
    else:
        return None

    if args['name'] is not None:
        map_args['name'] = args['name']
    else:
        return None

    map_args.update({
        'ami_id': args['ami_id'] if args['ami_id'] is not None else AWS_AMI_ID,
        'created_by': args['created_by'] if args['created_by'] is not None else getpass.getuser(),
        'spot_price': args['spot_price'] if args['spot_price'] is not None else None,
        'user_data': get_script(args['bash_script'] if args['bash_script'] is not None else BASH_SCRIPT_CLEAN)})

    return map_args


def main():
    parser = argparse.ArgumentParser('Start a number of CLEAN servers')
    parser.add_argument('-a', '--ami_id', help='the AMI id to use')
    parser.add_argument('-i', '--instance_type', required=True, help='the instance type to use')
    parser.add_argument('-c', '--created_by', help='the username to use')
    parser.add_argument('-n', '--name', required=True, help='the instance name to use')
    parser.add_argument('-s', '--spot_price', type=float, help='the spot price to use')
    parser.add_argument('-b', '--bash_script', help='the bash script to use')
    parser.add_argument('obs_id', nargs='1', help='the observation id')
    parser.add_argument('frequencies', nargs='+', help='the frequencies to use')

    args = vars(parser.parse_args())

    args1 = check_args(args)
    if args1 is None:
        LOG.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(args1['ami_id'], args1['user_data'], args1['instance_type'], args1['obs_id'], args1['frequencies'], args1['created_by'], args1['name'], args1['spot_price'])

if __name__ == "__main__":
    # -i r3.xlarge -n "Kevin clean test" -s 0.10 obs-1 vis1407~vis1411 vis_1411~1415 vis_1415~1419
    main()
