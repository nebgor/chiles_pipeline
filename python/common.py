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
Common code
"""
from email.mime.text import MIMEText
import multiprocessing
from os.path import join, expanduser, dirname
import re
import unicodedata
import time

from fabric.api import settings, cd, sudo, run
from fabric.utils import fastprint, puts

from config import USERNAME, AWS_KEY, PIP_PACKAGES


LOG = multiprocessing.log_to_stderr()
LOG.setLevel(multiprocessing.SUBDEBUG)


class Consumer(multiprocessing.Process):
    """
    A class to process jobs from the queue
    """
    def __init__(self, queue):
        multiprocessing.Process.__init__(self)
        self._queue = queue

    def run(self):
        """
        Sit in a loop
        """
        while True:
            LOG.info('Getting a task')
            next_task = self._queue.get()
            if next_task is None:
                # Poison pill means shutdown
                LOG.info('Exiting')
                self._queue.task_done()
                return
            LOG.info('Executing the task')
            next_task()
            self._queue.task_done()


def make_safe_filename(name):
    if isinstance(name, unicode):
        name = unicodedata.normalize('NFKD', name)
        name = name.encode('ascii', 'ignore').lower()
    else:
        name = name.lower()
    name = re.sub(r'[^a-z0-9]+', '-', name).strip('-')
    name = re.sub(r'[-]+', '-', name)

    return name


def get_boto_data():
    dot_boto = join(expanduser('~'), '.boto')
    with open(dot_boto, 'r') as my_file:
        data = my_file.read()

    return data


def get_script(file_name):
    """
    Get the script from the bash directory
    """
    here = dirname(__file__)
    bash = join(here, '../bash', file_name)
    with open(bash, 'r') as my_file:
        data = my_file.read()

    return data


def get_cloud_init():
    return MIMEText('''
#cloud-config
repo_update: true
repo_upgrade: all

# Install additional packages on first boot
packages:
 - wget
 - git
 - python-pip

# Log all cloud-init process output (info & errors) to a logfile
output : { all : ">> /var/log/chiles-output.log" }

# Final_message written to log when cloud-init processes are finished
final_message: "System boot (via cloud-init) is COMPLETE, after $UPTIME seconds. Finished at $TIMESTAMP"
''')


def setup_boto(hostname):
    LOG.info('Waiting for the ssh daemon to start up')
    for i in range(12):
        fastprint('.')
        time.sleep(5)
    puts('.')
    with settings(user=USERNAME, key_filename=AWS_KEY, host_string=hostname, connection_attempts=5):
        with cd('/home/ec2-user/chiles_pipeline'):
            run('git pull')
        sudo('pip install {0}'.format(PIP_PACKAGES))
        run('''echo "{0}
" > /home/ec2-user/.boto'''.format(get_boto_data()))
