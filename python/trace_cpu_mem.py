#!/mnt/gleam/chen/pyws/bin/python
#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2014
#    Copyright by UWA (in the framework of the ICRAR)
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
# ******************************************************************************
#
#
# Who       When        What
# --------  ----------  -------------------------------------------------------
# cwu      31/Mar/2014  Created
#

"""
trace cpu, memory usage and io info from /proc
"""
from collections import namedtuple
from optparse import OptionParser
import os
import sys
import time
import commands
import gc
import signal
import cPickle as pickle


# indices from the line
# Specs - https://www.kernel.org/doc/Documentation/filesystems/proc.txt
I_UT = 13
I_ST = 14
I_CUT = 15
I_CST = 16
I_VM = 22
I_RSS = 23
I_STATE = 2
I_BLKIO = 41

I_SYSCR = 2
I_SYSCW = 3
I_READ_BYTES = 4
I_WRITE_BYTES = 5
I_CANCELLED_WRITE_BYTES = 6

FSTAT = '/proc/stat'

"""
ts:          time stamp
u:           user cpu of this process
k:           kernel cpu of this process
cu:          user cpu of child process
ck:          kernel cpu of child process
all:         cpu of all processes
vm:          virtual memory size
rss:         resident set size (memory portion)
state:       state (R is running, S is sleeping, D is sleeping in an uninterruptible wait, Z is zombie, T is traced or stopped)
blkio:       time spent waiting for block IO
syscr:       Attempt to count the number of read I/O operations, i.e. syscalls like read() and pread()
syscw:       Attempt to count the number of write I/O operations, i.e. syscalls like write() and pwrite()
read_bytes:  Attempt to count the number of bytes which this process really did cause to be fetched from the storage layer. Done at the submit_bio() level,
             so it is accurate for block-backed filesystems.
write_bytes: Attempt to count the number of bytes which this process caused to be sent to the storage layer. This is done at page-dirtying time.
cancelled_write_bytes: The big inaccuracy here is truncate. If a process writes 1MB to a file and then deletes the file, it will in fact perform no writeout. But it will have
                       been accounted as having caused 1MB of write. In other words: The number of bytes which this process caused to not happen,
                       by truncating pagecache. A task can cause "negative" IO too. If this task truncates some dirty pagecache, some IO which another task has been accounted
                       for (in its write_bytes) will not be happening. We _could_ just subtract that from the truncating task's write_bytes, but there is information loss in doing that.
"""
pstat = namedtuple('pstat', 'ts u k cu ck all vm rss state blkio syscr syscw read_bytes write_bytes cancelled_write_bytes')
ps = []


def exec_cmd(cmd, fail_on_error=True):
    re = commands.getstatusoutput(cmd)
    if re[0] != 0:
        err_msg = 'Fail to execute command: "%s". Exception: %s' % (cmd, re[1])
        if fail_on_error:
            raise Exception(err_msg)
        else:
            print err_msg
    return re


def get_sys_page_size():
    cmd = "getconf PAGESIZE"
    re = exec_cmd(cmd)
    return int(re[1])


def print_sample(spl_list):
    """
    This is for testing

    splList    a list of samples (list)
    """
    from prettytable import PrettyTable
    tbl = PrettyTable(["Time stamp", "User CPU", "Kernel CPU", "U-Child CPU",
                       "K-Child CPU", "All CPUs", "VM", "RSS", "State", "BlkIO",
                       "syscr", "syscw", "read_bytes", "write_bytes", "cancelled_write_bytes"])
    tbl.padding_width = 1   # One space between column edges and contents (default)

    for p in spl_list:
        tbl.add_row([p.ts, p.u, p.k, p.cu, p.ck, p.all, p.vm, p.rss, p.state, p.blkio,
                     p.syscr, p.syscw, p.read_bytes, p.write_bytes, p.cancelled_write_bytes])

    print tbl


def compute_usage(spl_list, print_list=False, save_to_file=None):
    """
    Convert from sample to CPU/memory usage

    splList    sample list (a list of samples (pstat))
    Return:    a list of statistics (tuples[timestamp, total_cpu, kernel_cpu, vm, rss])
    """
    pgsz = get_sys_page_size()
    result_list = []
    leng = len(spl_list)
    if leng < 2:
        raise Exception("sample size is too small")
    # refer to http://stackoverflow.com/questions/4189123/python-how-to-get-number-of-mili-seconds-per-jiffy
    # refer to http://stackoverflow.com/questions/16726779/total-cpu-usage-of-an-application-from-proc-pid-stat
    hertz = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
    gc.disable()
    for i in range(leng - 1):
        sp1 = spl_list[i]
        sp2 = spl_list[i + 1]

        tcpu1 = sp1.u + sp1.k + sp1.cu + sp1.ck
        tcpu2 = sp2.u + sp2.k + sp2.cu + sp2.ck
        kcpu1 = sp1.k + sp1.ck
        kcpu2 = sp2.k + sp2.ck

        ios1 = sp1.syscr + sp1.syscw
        ios2 = sp2.syscr + sp2.syscw

        iod1 = sp1.read_bytes + sp1.write_bytes - sp1.cancelled_write_bytes
        iod2 = sp2.read_bytes + sp2.write_bytes - sp2.cancelled_write_bytes

        # print 'ios2: {0}, ios1: {1}, iod2: {2}, iod1: {3}'.format(ios2, ios1, iod2, iod1)
        # allcpu =  float(sp2.all - sp1.all)
        walltime = 1    # 1 seconds
        tu = int(100.0 * (tcpu2 - tcpu1) / hertz / walltime)
        ku = int(100.0 * (kcpu2 - kcpu1) / hertz / walltime)

        iops = (ios2 - ios1) / hertz / walltime
        iod = (iod2 - iod1) / hertz / walltime

        if ios2 == ios1:
            io_wait = 0
        else:
            io_wait = (sp2.blkio - sp1.blkio) / (ios2 - ios1) * 1000.0 / hertz

        itm = (sp2.ts, tu, ku, sp2.vm, pgsz * sp2.rss, iops, iod, io_wait)
        result_list.append(itm)
    gc.enable()

    if print_list:
        from prettytable import PrettyTable
        tbl = PrettyTable(["Time stamp", "Total CPU %", "Kernel CPU %", "VM", "RSS", "IOPS", "Bytes/S", "IO WAIT"])
        tbl.padding_width = 1

        for p in result_list:
            tbl.add_row([p[0], p[1], p[2], p[3], p[4], p[5], p[6], p[7]])

        print tbl

    if save_to_file:
        print 'Saving CPU statistics to file %s ...' % save_to_file
        try:
            output = open(save_to_file, 'wb')
            start_save_time = time.time()
            pickle.dump(result_list, output)
            output.close()
            print 'Time for saving CPU statistics: %.2f' % (time.time() - start_save_time)
        except Exception, e:
            ex = str(e)
            print 'Fail to save CPU statistics to file %s: %s' % (save_to_file, ex)

    return result_list


def process_sample(raw_sample):
    """
    Convert a raw sample into
    a sample tuple with proper fields (k-v pair)

    https://www.kernel.org/doc/Documentation/filesystems/proc.txt

    /proc/stat fields specification
    Time units are in USER_HZ (typically hundredths of a second)
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
    pa_line = raw_sample[0]
    cpu_line = raw_sample[1].replace('cpu', '')
    ts = raw_sample[2]
    io_details = raw_sample[3]

    pa = pa_line.split()
    cpus = [int(x) for x in cpu_line.split()]
    all_cpus = sum(cpus)

    ret = pstat(ts,
                int(pa[I_UT]),
                int(pa[I_ST]),
                int(pa[I_CUT]),
                int(pa[I_CST]),
                all_cpus,
                int(pa[I_VM]),
                int(pa[I_RSS]),
                pa[I_STATE],
                int(pa[I_BLKIO]),
                int(io_details[I_SYSCR].split()[1]),
                int(io_details[I_SYSCW].split()[1]),
                int(io_details[I_READ_BYTES].split()[1]),
                int(io_details[I_WRITE_BYTES].split()[1]),
                int(io_details[I_CANCELLED_WRITE_BYTES].split()[1]),
                )

    return ret


def collect_sample(pid):
    """
    retrieve current usage sample
    This will be called every N seconds

    pid:        process id (int)
                (this should have been validated before calling this function)

    Return:    an instance of the pstat namedtuple
    """
    time_stamp = time.time()
    file_name1 = "/proc/%d/stat" % pid
    with open(file_name1) as f:
        lines1 = f.readlines()

    file_name2 = "/proc/%d/io" % pid
    with open(file_name2) as f:
        lines2 = f.readlines()

    with open(FSTAT, 'r') as f:
        first_line = f.readline()

    """
    # will this ever happen at all?
    if (not lines or len(lines) < 1):
        raise Exception('Cannot read file: %s' % fname)

    if (not first_line or len(first_line) < 1):
        raise Exception('Cannot read file: %s' % FSTAT)
    """
    return [lines1[0], first_line, time_stamp, lines2]


def _test_get_sample(test_sample):
    for i in range(10):
        now = time.time()
        ps.append(collect_sample(test_sample.pid))
        time.sleep(1 - (time.time() - now))

    pas = [process_sample(x) for x in ps]
    print_sample(pas)
    compute_usage(pas, print_list=True)


def exit_handler(signum, frame):
    """
    ps:    raw samples
    """
    print "Receiving signal ", signum, " ", frame

    print "Processing samples ..."
    pas = [process_sample(x) for x in ps]
    print "Compute CPU statistics ..."
    compute_usage(pas, print_list=False, save_to_file=options.save_cpu_file)
    exit(0)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-p", "--pid", action="store", type="int", dest="pid")
    parser.add_option("-o", "--outputfile", action="store", dest="save_cpu_file", type="string", default="", help="Save CPU stats to the file")

    (options, args) = parser.parse_args()
    if None == options.pid or None == options.save_cpu_file:
        parser.print_help()
        sys.exit(1)

    fname = '/proc/%d/stat' % options.pid
    if not os.path.exists(fname):
        print "Process with pid %d is not running!" % options.pid
        sys.exit(1)

    # _test_get_sample(options)

    signal.signal(signal.SIGTERM, exit_handler)
    signal.signal(signal.SIGINT, exit_handler)

    while True:
        start_time = time.time()
        try:
            sp = collect_sample(options.pid)
            ps.append(sp)
        except IOError, ioe:
            print ("Error occured %s" % str(ioe))
            exit_handler(15, None)   # the process has terminated, so finish CPU monitoring...

        time.sleep(1 - (time.time() - start_time))
