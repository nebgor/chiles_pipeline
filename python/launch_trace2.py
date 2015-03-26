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
    https://www.kernel.org/doc/Documentation/filesystems/proc.txt

    /proc/stat fields specification
    The very first  "cpu" line aggregates the  numbers in all  of the other "cpuN"
    lines.  These numbers identify the amount of time the CPU has spent performing
    different kinds of work.  Time units are in USER_HZ (typically hundredths of a
    second).  The meanings of the columns are as follows, from left to right:

    - user: normal processes executing in user mode
    - nice: niced processes executing in user mode
    - system: processes executing in kernel mode
    - idle: twiddling thumbs
    - iowait: waiting for I/O to complete
    - irq: servicing interrupts
    - softirq: servicing softirqs
    - steal: involuntary wait
    - guest: running a normal guest
    - guest_nice: running a niced guest

    /proc/PID/stat fields specification
    Field          Content
      pid           process id
      tcomm         filename of the executable
      state         state (R is running, S is sleeping, D is sleeping in an
                    uninterruptible wait, Z is zombie, T is traced or stopped)
      ppid          process id of the parent process
      pgrp          pgrp of the process
      sid           session id
      tty_nr        tty the process uses
      tty_pgrp      pgrp of the tty
      flags         task flags
      min_flt       number of minor faults
      cmin_flt      number of minor faults with child's
      maj_flt       number of major faults
      cmaj_flt      number of major faults with child's
      utime         user mode jiffies
      stime         kernel mode jiffies
      cutime        user mode jiffies with child's
      cstime        kernel mode jiffies with child's
      priority      priority level
      nice          nice level
      num_threads   number of threads
      it_real_value    (obsolete, always 0)
      start_time    time the process started after system boot
      vsize         virtual memory size
      rss           resident set memory size
      rsslim        current limit in bytes on the rss
      start_code    address above which program text can run
      end_code      address below which program text can run
      start_stack   address of the start of the main process stack
      esp           current value of ESP
      eip           current value of EIP
      pending       bitmap of pending signals
      blocked       bitmap of blocked signals
      sigign        bitmap of ignored signals
      sigcatch      bitmap of caught signals
      wchan         address where process went to sleep
      0             (place holder)
      0             (place holder)
      exit_signal   signal to send to parent thread on exit
      task_cpu      which CPU the task is scheduled on
      rt_priority   realtime priority
      policy        scheduling policy (man sched_setscheduler)
      blkio_ticks   time spent waiting for block IO
      gtime         guest time of the task in jiffies
      cgtime        guest time of the task children in jiffies
      start_data    address above which program data+bss is placed
      end_data      address below which program data+bss is placed
      start_brk     address above which program heap can be expanded with brk()
      arg_start     address above which program command line is placed
      arg_end       address below which program command line is placed
      env_start     address above which program environment is placed
      env_end       address below which program environment is placed
      exit_code     the thread's exit_code in the form reported by the waitpid system call

"""

import logging
import os
from os import makedirs
import subprocess
import sys
from os.path import exists, join
import time
from datetime import datetime
from psutil import Process
import resource
from sqlalchemy import create_engine, MetaData, Table, Column, Float, Integer, String

I_STATE = 2
I_UTIME = 13
I_STIME = 14
I_CUTIME = 15
I_CSTIME = 16
I_PRIORITY = 17
I_NICE = 18
I_NUM_THREADS = 19
I_VSIZE = 22
I_RSS = 23
I_BLKIO_TICKS = 41

TRACE_METADATA = MetaData()
LOG_DETAILS = Table(
    'log_details',
    TRACE_METADATA,
    Column('log_details_id', Integer, primary_key=True),
    Column('pid', Integer, index=True, nullable=False),
    Column('timestamp', Float, index=True, nullable=False),
    Column('state', String(2), nullable=False),
    Column('utime', Integer, nullable=False),
    Column('stime', Integer, nullable=False),
    Column('cutime', Integer, nullable=False),
    Column('cstime', Integer, nullable=False),
    Column('priority', Integer, nullable=False),
    Column('nice', Integer, nullable=False),
    Column('num_threads', Integer, nullable=False),
    Column('vsize', Integer, nullable=False),
    Column('rss', Integer, nullable=False),
    Column('blkio_ticks', Integer, nullable=False),
    Column('read_count', Integer, nullable=False),
    Column('write_count', Integer, nullable=False),
    Column('read_bytes', Integer, nullable=False),
    Column('write_bytes', Integer, nullable=False),
    sqlite_autoincrement=True
)
STAT_DETAILS = Table(
    'stat_details',
    TRACE_METADATA,
    Column('stat_details_id', Integer, primary_key=True),
    Column('timestamp', Float, index=True, nullable=False),
    Column('user', Integer, nullable=False),
    Column('nice', Integer, nullable=False),
    Column('system', Integer, nullable=False),
    Column('idle', Integer, nullable=False),
    Column('iowait', Integer, nullable=False),
    Column('irq', Integer, nullable=False),
    Column('softirq', Integer, nullable=False),
    Column('steal', Integer, nullable=False),
    Column('guest', Integer, nullable=False),
    Column('guest_nice', Integer, nullable=False),
    sqlite_autoincrement=True
)
PROCESS_DETAILS = Table(
    'process_details',
    TRACE_METADATA,
    Column('process_details_id', Integer, primary_key=True),
    Column('pid', Integer, index=True, nullable=False),
    Column('ppid', Integer, index=True, nullable=False),
    Column('name', String(256), nullable=False),
    Column('cmd_line', String(2000), nullable=False),
    Column('create_time', Float, nullable=False),
    sqlite_autoincrement=True
)
TRACE_DETAILS = Table(
    'trace_details',
    TRACE_METADATA,
    Column('start_time', Float, nullable=False),
    Column('cmd_line', String(2000), nullable=False),
    Column('sample_rate', Float, nullable=False),
    Column('tick', Integer, nullable=False),
    Column('page_size', Integer, nullable=False)
)

FSTAT = '/proc/stat'
EPOCH = datetime(1970, 1, 1)
LOGS_DIR = '/tmp/trace_logs'
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)


class Trace():
    def __init__(self, command_list, sample_rate=1):
        self._command_list = command_list
        self._sample_rate = sample_rate
        self._connection = None
        self._set_pids = set()
        self._insert_log_details = LOG_DETAILS.insert()

        # Create the logs directory
        LOG.info("Checking for the logs directory {0}".format(LOGS_DIR))
        if not exists(LOGS_DIR):
            LOG.info("Creating the logs directory {0}".format(LOGS_DIR))
            makedirs(LOGS_DIR)

    def _get_samples(self, list_processes):
        transaction = self._connection.begin()

        # Read the data from /proc/stat for the system
        with open(FSTAT, 'r') as f:
            first_line = f.readline()
        first_line.split()
        time_stamp = (datetime.now() - EPOCH).total_seconds()
        self._connection.execute(
            STAT_DETAILS.insert(),
            timestamp=time_stamp,
            user=first_line[1],
            nice=first_line[2],
            system=first_line[3],
            idle=first_line[4],
            iowait=first_line[5],
            irq=first_line[6],
            softirq=first_line[7],
            steal=first_line[8],
            guest=first_line[9],
            guest_nice=first_line[10]
        )

        # Now do the individual processes
        for process in list_processes:
            pid = process.pid
            if pid not in self._set_pids:
                self._set_pids.add(pid)

                self._connection.execute(
                    PROCESS_DETAILS.insert(),
                    pid=pid,
                    ppid=process.ppid(),
                    name=process.name(),
                    cmd_line=' '.join(process.cmdline()),
                    create_time=process.create_time(),
                )

            self._collect_sample(pid, time_stamp)

        transaction.commit()

    def _collect_sample(self, pid, time_stamp):
        file_name1 = "/proc/{0}/stat".format(pid)
        with open(file_name1) as f:
            line1 = f.readline()
        stat_details = line1.split()

        pid_process = Process(pid)
        io_counters = pid_process.io_counters()

        self._connection.execute(
            self._insert_log_details,
            pid=pid,
            timestamp=time_stamp,
            state=stat_details[I_STATE],
            utime=stat_details[I_UTIME],
            stime=stat_details[I_STIME],
            cutime=stat_details[I_CUTIME],
            cstime=stat_details[I_CSTIME],
            priority=stat_details[I_PRIORITY],
            nice=stat_details[I_NICE],
            num_threads=stat_details[I_NUM_THREADS],
            vsize=stat_details[I_VSIZE],
            rss=stat_details[I_RSS],
            blkio_ticks=stat_details[I_BLKIO_TICKS],
            read_count=io_counters.read_count,
            write_count=io_counters.write_count,
            read_bytes=io_counters.read_bytes,
            write_bytes=io_counters.write_bytes
        )

    def run(self):
        # Get the start time
        start_time = datetime.now()

        # Spin up the main process
        sp = subprocess.Popen(self._command_list)

        # Open the sqlite database
        sqlite_file = join(LOGS_DIR, '{0}_{1}_log.db'.format(start_time.strftime('%Y%m%d%H%M%S'), sp.pid))
        engine = create_engine('sqlite:///{0}'.format(sqlite_file))
        self._connection = engine.connect()
        TRACE_METADATA.create_all(self._connection)

        # Store the trace details
        self._connection.execute(
            TRACE_DETAILS.insert(),
            start_time=(start_time - EPOCH).total_seconds(),
            cmd_line=' '.join(self._command_list),
            sample_rate=self._sample_rate,
            tick=os.sysconf(os.sysconf_names['SC_CLK_TCK']),
            page_size=resource.getpagesize()
        )

        try:
            main_process = Process(sp.pid)
            while sp.poll() is None:
                now = time.time()

                pids = [Process(sp.pid)]
                pids.extend(main_process.children(recursive=True))
                self._get_samples(pids)

                time.sleep(max(1 - (time.time() - now), 0.001))
        finally:
            self._connection.close()


def usage():
    LOG.info('python launch_trace.py app')
    LOG.info('e.g. python launch_trace.py ls -l')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    trace = Trace(sys.argv[1:])
    trace.run()
