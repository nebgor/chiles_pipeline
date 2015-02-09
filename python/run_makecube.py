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
Run the makecube task
"""
import argparse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import getpass

from common import LOGGER, make_safe_filename, get_script, get_cloud_init, setup_boto_and_git
from config import AWS_AMI_ID, BASH_SCRIPT_MAKECUBE
from ec2_helper import EC2Helper


def get_mime_encoded_user_data(data, observation_id):
    """
    AWS allows for a multipart m
    """
    # Build the mime message
    user_data = MIMEMultipart()
    user_data.attach(get_cloud_init())

    data_formatted = data.format(observation_id)
    user_data.attach(MIMEText(data_formatted))
    return user_data.as_string()


def start_servers(ami_id, user_data, instance_type, obs_id, created_by, name, spot_price=None):
    LOGGER.info('obs_id: {0}'.format(obs_id))
    ec2_helper = EC2Helper()
    user_data_mime = get_mime_encoded_user_data(user_data, obs_id)
    if spot_price is not None:
        ec2_instance = ec2_helper.run_spot_instance(
            ami_id,
            spot_price,
            user_data_mime,
            instance_type, None,
            created_by,
            name + '- {0}'.format(obs_id),
            ephemeral=True)
    else:
        ec2_instance = ec2_helper.run_instance(
            ami_id,
            user_data_mime,
            instance_type,
            None,
            created_by,
            name + '- {0}'.format(obs_id),
            ephemeral=True)

    # Setup boto via SSH so we don't pass our keys etc in "the clear"
    setup_boto_and_git(ec2_instance.ip_address)


def check_args(args):
    """
    Check the arguments and prompt for new ones
    """
    map_args = {}

    if args['obs_id'] is None:
        return None

    if args['instance_type'] is None:
        return None

    if args['name'] is None:
        return None

    map_args.update({
        'ami_id': args['ami_id'] if args['ami_id'] is not None else AWS_AMI_ID,
        'created_by': args['created_by'] if args['created_by'] is not None else getpass.getuser(),
        'spot_price': args['spot_price'] if args['spot_price'] is not None else None,
        'user_data': get_script(args['bash_script'] if args['bash_script'] is not None else BASH_SCRIPT_MAKECUBE)})

    return map_args


def main():
    parser = argparse.ArgumentParser('Start a number of CLEAN servers')
    parser.add_argument('-a', '--ami_id', help='the AMI id to use')
    parser.add_argument('-i', '--instance_type', required=True, help='the instance type to use')
    parser.add_argument('-c', '--created_by', help='the username to use')
    parser.add_argument('-n', '--name', required=True, help='the instance name to use')
    parser.add_argument('-s', '--spot_price', type=float, help='the spot price to use')
    parser.add_argument('-b', '--bash_script', help='the bash script to use')
    parser.add_argument('obs_id', help='the observation id')

    args = vars(parser.parse_args())

    corrected_args = check_args(args)
    if corrected_args is None:
        LOGGER.error('The arguments are incorrect: {0}'.format(args))
    else:
        start_servers(
            corrected_args['ami_id'],
            corrected_args['user_data'],
            args['instance_type'],
            make_safe_filename(args['obs_id']),
            corrected_args['created_by'],
            args['name'],
            corrected_args['spot_price'])

if __name__ == "__main__":
    # -i r3.xlarge -n "Kevin ImgConcat test" -s 0.10 obs-1
    main()

