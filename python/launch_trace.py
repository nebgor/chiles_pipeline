import logging
from os import makedirs
import subprocess
import sys
from os.path import exists, join
import time
import datetime
from psutil import Process
from trace_cpu_mem import collect_sample, process_sample, compute_usage

MAP_SAMPLES = {}
LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)


def usage():
    print 'python launch_trace.py app'
    print 'e.g. python launch_trace.py ls -l'


def get_samples(list_pids):
    for pid in list_pids:
        LOG.INFO('Sampling {0}'.format(pid))
        samples = MAP_SAMPLES.get(pid)
        if samples is None:
            samples = []
            MAP_SAMPLES[pid] = samples

        samples.append(collect_sample(pid))


def trace():
    start_time = datetime.datetime.now()

    # Spin up the main process
    cmd_list = sys.argv[1:]
    sp = subprocess.Popen(cmd_list)
    main_process = Process(sp.pid)
    while sp.poll() is None:
        now = time.time()

        pids = [sp.pid]
        pids.extend(main_process.children(recursive=True))
        get_samples(pids)

        time.sleep(max(1 - (time.time() - now), 0.001))

    logs_dir = '/tmp/trace_logs'
    print "Checking for the logs directory ", logs_dir
    if not exists(logs_dir):
        print "Creating the logs directory ", logs_dir
        makedirs(logs_dir)

    for key in MAP_SAMPLES.keys():
        LOG.info('Writing data for {0}'.format(key))
        if sp.pid == key:
            cpu_logfile = join(logs_dir, '{0}_{1}_cpu.log'.format(start_time.strftime('%Y%m%d%H%M%S'), sp.pid))
        else:
            cpu_logfile = join(logs_dir, '{0}_{1}_{2}_cpu.log'.format(start_time.strftime('%Y%m%d%H%M%S'), sp.pid, key))

        LOG.info("Processing samples ...")
        pas = [process_sample(x) for x in MAP_SAMPLES.get(key)]
        LOG.info("Compute CPU statistics ...")
        compute_usage(pas, print_list=False, save_to_file=cpu_logfile)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    trace()
