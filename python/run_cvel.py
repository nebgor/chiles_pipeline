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
from os.path import dirname, join
import sys
from config import AWS_AMI_ID, BASH_SCRIPT_CVEL
from ec2_helper import EC2Helper

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)
LOG.info('PYTHONPATH = {0}'.format(sys.path))


def start_servers(ami_id, user_data, instance_type, volume_ids, created_by, name, spot_price=None):
    ec2_helper = EC2Helper()
    count = 1
    for volume_id in volume_ids:
        # Get the name of the volume
        volume_name = ec2_helper.get_volume_name(volume_id)
        user_data_mime = get_mime_encoded_user_data(user_data, volume_name)

        if spot_price is not None:
            ec2_helper.run_spot_instance(ami_id, spot_price, user_data_mime, instance_type, volume_id, created_by, name + ' {0}'.format(count), ephemeral=True)
        else:
            ec2_helper.run_instance(ami_id, user_data_mime, instance_type, volume_id, created_by, name + ' {0}'.format(count), ephemeral=True)

        count += 1


def get_mime_encoded_user_data(data, volume_name):
    """
    AWS allows for a multipart m
    """
    user_data = MIMEMultipart()

    cloud_init = MIMEText('''
#cloud-config

# Install additional packages on first boot
packages:
 - wget
 - git

# Log all cloud-init process output (info & errors) to a logfile
output : { all : ">> /var/log/chiles-output.log" }

# Final_message written to log when cloud-init processes are finished
final_message: "System boot (via cloud-init) is COMPLETE, after $UPTIME seconds. Finished at $TIMESTAMP"
''')
    user_data.attach(cloud_init)
    data_formatted = data.format(volume_name)
    user_data.attach(MIMEText(data_formatted))
    return user_data.as_string()


def get_script(file_name):
    """
    AWS allows for a multipart m
    """
    here = dirname(__file__)
    bash = join(here, '../bash', file_name)
    with open(bash, 'r') as my_file:
        data = my_file.read()

    return data


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}

    if args['vol_ids'] is not None:
        map_args['vol_ids'] = args['vol_ids']
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
    parser.add_argument('vol_ids', nargs='+', help='the volume ids to use')

    args = vars(parser.parse_args())

    args1 = check_args(args)
    if args1 is None:
        LOG.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(args1['ami_id'], args1['user_data'], args1['instance_type'], args1['vol_ids'], args1['created_by'], args1['name'], args1['spot_price'])

if __name__ == "__main__":
    main()
