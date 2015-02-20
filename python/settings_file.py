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
Chiles settings
"""
from os.path import exists, dirname, expanduser
from configobj import ConfigObj

CHILES_CVEL_OUTPUT = '/mnt/output/Chiles/split_vis'
CHILES_CLEAN_OUTPUT = '/mnt/output/Chiles/split_cubes'
CHILES_IMGCONCAT_OUTPUT = '/mnt/output/Chiles'
CHILES_BUCKET_NAME = 'chiles.output.icrar.org'
CHILES_LOGS = '/home/ec2-user/Chiles/casa_work_dir'

AWS_KEY = expanduser('~/.ssh/aws-chiles-sydney.pem')
PIP_PACKAGES = 'configobj boto'
USERNAME = 'ec2-user'

FREQUENCY_WIDTH = 4
FREQUENCY_GROUPS = []

for bottom_freq in range(1200, 1424, FREQUENCY_WIDTH):
    FREQUENCY_GROUPS.append([bottom_freq, bottom_freq + FREQUENCY_WIDTH])

AWS_AMI_ID = None
AWS_KEY_NAME = None
AWS_SECURITY_GROUPS = None
AWS_SUBNET_ID = None
AWS_REGION = None

BASH_SCRIPT_CVEL = None
BASH_SCRIPT_CLEAN = None
BASH_SCRIPT_MAKECUBE = None
BASH_SCRIPT_SETUP_DISKS = 'setup_disks.bash'

# [vCPU, Mem, Num Disks, Size]
AWS_INSTANCES = {
    'm3.medium': [1, 3.75, 1, 4],
    'm3.large': [2, 7.5, 1, 32],
    'm3.xlarge': [4, 15, 2, 40],
    'm3.2xlarge': [8, 30, 2, 80],
    'c3.large': [2, 3.75, 2, 16],
    'c3.xlarge': [4, 7.5, 2, 40],
    'c3.2xlarge': [8, 15, 2, 80],
    'c3.4xlarge': [16, 30, 2, 160],
    'c3.8xlarge': [32, 60, 2, 320],
    'r3.large': [2, 15, 1, 32],
    'r3.xlarge': [4, 30.5, 1, 80],
    'r3.2xlarge': [8, 61, 1, 160],
    'r3.4xlarge': [16, 122, 1, 320],
    'r3.8xlarge': [32, 244, 2, 320],
}

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

    OBS_IDS = config['obs_ids']
