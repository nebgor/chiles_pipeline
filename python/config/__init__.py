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

"""
from os.path import exists, dirname, expanduser
from configobj import ConfigObj

CHILES_CVEL_OUTPUT = '/mnt/output/Chiles/split_vis'
CHILES_CLEAN_OUTPUT = '/mnt/output/Chiles/split_cubes'
#CHILES_CVEL_OUTPUT = '/Users/kevinvinsen/Downloads/mnt/output/Chiles/split_vis'
CHILES_BUCKET_NAME = 'icrar.chiles.output'

AWS_KEY = expanduser('~/.ssh/icrar_sydney.pem')
PIP_PACKAGES = 'fabric configobj boto'
USERNAME = 'ec2-user'

AWS_AMI_ID = None
AWS_KEY_NAME = None
AWS_SECURITY_GROUPS = None
AWS_SUBNET_ID = None
AWS_REGION = None

BASH_SCRIPT_CVEL = None
BASH_SCRIPT_CLEAN = None
BASH_SCRIPT_MAKECUBE = None

config_file_name = dirname(__file__) + '/chiles.settings'
if exists(config_file_name):
    config = ConfigObj(config_file_name)

    # Get the AWS details
    AWS_AMI_ID = config['ami_id']
    AWS_KEY_NAME = config['key_name']
    AWS_SECURITY_GROUPS = config['security_groups']
    AWS_SUBNET_ID = config['subnet_id']
    AWS_REGION = config['region']

    BASH_SCRIPT_CVEL = config['bash_script_cvel']
    BASH_SCRIPT_CLEAN = config['bash_script_clean']
    BASH_SCRIPT_MAKECUBE = config['bash_script_makecube']
