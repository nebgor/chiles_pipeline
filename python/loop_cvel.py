"""
Taken from makecube.py extracting the loop over cvel

This module should run together with the casapy: e.g. casapy --nologger -c loop_cvel.py
"""


#execfile('/home/ec2-user/chiles_pipeline/python/makecube_defines.py')

import os
import sys
print 'Sys Path: ' + str(sys.path)

base_path = os.path.dirname(__file__)
sys.path.append(os.path.abspath(base_path))
print 'Sys Path: ' + str(sys.path)
from makecube_defines import *

print 'test'+INPUT_VIS_SUFFIX
# loop through selected obs and cvel. Uses obId to only do subset of possible

checkDir(job_id, vis_dirs)
checkDir(job_id, vis_bk_dirs)
#checkDir(job_id, cube_dir)
#checkDir(job_id, out_dir)

obs_list, all_obs = getMyObs(job_id, obs_dir, obs_first, obs_last, num_jobs)
obsId_list = []

print "myobs = \t%s\nvis_dirs = \t%s\nrun_id = \t%s" % (str(obs_list), vis_dirs, run_id)


for obs in obs_list:
    infile_dir = '%s/%s' % (obs_dir, obs)
    lsre = execCmd('ls %s' % infile_dir)

    infile = None
    for ff in lsre[1].split('\n'):
         if (ff.endswith(INPUT_VIS_SUFFIX)):
             infile = '%s/%s' % (infile_dir, ff)
    if (not infile):
        print 'No measurementSet file found under %s' % infile_dir
        continue

    obsId = os.path.basename(infile_dir).replace('_FINAL_PRODUCTS', '')
    obsId_list.append(obsId)
    outdir = '%s/%s/' % (vis_dirs, obsId)
    backup_dir = '%s/%s/' % (vis_bk_dirs, obsId)
    do_cvel(infile, outdir, backup_dir, freq_min,
             freq_max, freq_step, freq_width, spec_window, obsId)

# wait until all other cvel processes are done before quite:
done_obs = checkIfAllObsSplitDone(casa_workdir, job_id, run_id, all_obs, timeout = split_tmout)

    # Done
