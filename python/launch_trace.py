from os import makedirs
import subprocess
import sys
from os.path import exists, join
import datetime


def usage():
    print 'python launch_trace.py app'
    print 'e.g. python launch_trace.py ls -l'


def trace():
    cmd_list = sys.argv[1:]
    start_time = datetime.datetime.now()

    logs_dir = '/tmp/trace_logs'
    print "Checking for the logs directory ", logs_dir
    if not exists(logs_dir):
        print "Creating the logs directory ", logs_dir
        makedirs(logs_dir)

    cpu_logfile = join(logs_dir, '{0}_cpu.log'.format(start_time.strftime('%Y%m%d%H%M%S')))

    sp = subprocess.Popen(cmd_list)
    cmd1 = 'python trace_cpu_mem.py -o %s -p %d' % (cpu_logfile, sp.pid)
    cmd_list1 = cmd1.split()
    sp1 = subprocess.Popen(cmd_list1)

    print "Waiting...."
    print "Application return code:", sp.wait()
    print "trace_cpu_mem return code:", sp1.wait()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    trace()
