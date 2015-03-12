from os import makedirs
import subprocess
import sys
import calendar
import time

from os.path import exists, join


def usage():
    print 'python launch_trace.py app'
    print 'e.g. python launch_trace.py ls -l'


def trace():
    cmd_list = sys.argv[1:]
    start_time = calendar.timegm(time.gmtime())

    logs_dir = '/tmp/trace_logs'
    print "Checking for the logs directory ", logs_dir
    if not exists(logs_dir):
        print "Creating the logs directory ", logs_dir
        makedirs(logs_dir)

    # print "CPU recording start_time: ", start_time
    cpu_logfile = join(logs_dir, '%s_cpu.log' % str(start_time))
    app_logfile = join(logs_dir, '%s_app.log' % str(start_time))
    h_app_logfile = open(app_logfile, 'w')

    # sp = subprocess.Popen(cmd_list, stdout=h_app_logfile)
    sp = subprocess.Popen(cmd_list)
    cmd1 = 'python trace_cpu_mem.py -o %s -p %d' % (cpu_logfile, sp.pid)
    cmd_list1 = cmd1.split()
    subprocess.Popen(cmd_list1)

    print "Waiting...."
    print "Application return code:", sp.wait()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    trace()
