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
import getpass
import logging
import sys
from config import AWS_AMI_ID
from ec2_helper import EC2Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def start_servers(ami_id, user_data, instance_type, volume_id, created_by, name, spot_price=None):
    ec2_helper = EC2Helper()

    if spot_price is not None:
        ec2_helper.run_spot_instance(ami_id, spot_price, user_data, instance_type, volume_id, created_by, name, ephemeral=True)
    else:
        ec2_helper.run_instance(ami_id, user_data, instance_type, volume_id, created_by, name, ephemeral=True)


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}
    if args['ami_id'] is not None:
        map_args['ami_id'] = args['ami_id']
    else:
        map_args['ami_id'] = AWS_AMI_ID

    if args['vol_id'] is not None:
        map_args['vol_id'] = args['vol_id']
    else:
        return None

    if args['instance_type'] is not None:
        map_args['instance_type'] = args['instance_type']
    else:
        return None

    if args['created_by'] is not None:
        map_args['created_by'] = args['created_by']
    else:
        map_args['created_by'] = getpass.getuser()

    if args['name'] is not None:
        map_args['name'] = args['name']
    else:
        return None

    if args['spot_price'] is not None:
        map_args['spot_price'] = args['spot_price']
    else:
        map_args['spot_price'] = None

    map_args['user_data'] = '''
#!/bin/bash
echo 'Hello World'
'''

    return map_args


def main():
    parser = argparse.ArgumentParser('Start a number of CVEL servers')
    parser.add_argument('-a', '--ami_id', help='the AMI id to use')
    parser.add_argument('-v', '--vol_id', required=True, help='the volume id to use')
    parser.add_argument('-i', '--instance_type', required=True, help='the instance type to use')
    parser.add_argument('-c', '--created_by', help='the username to use')
    parser.add_argument('-n', '--name', required=True, help='the instance name to use')
    parser.add_argument('-s', '--spot_price', type=float, help='the spot price to use')

    args = vars(parser.parse_args())

    args1 = check_args(args)
    if args is None:
        LOG.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(args1['ami_id'], args1['user_data'], args1['instance_type'], args1['vol_id'], args1['created_by'], args1['name'], args1['spot_price'])

if __name__ == "__main__":
    main()

