"""
Taken from makecube.py extracting the loop over clean

This module should run together with the casapy: e.g. casapy --nologger -c loop_clean.py
"""
from glob import glob
import os

execfile('/home/ec2-user/chiles_pipeline/python/makecube_defines.py')

#base_path = os.path.dirname(__file__)
#sys.path.append(os.path.abspath(base_path))
#
#from makecube_defines import *

#checkDir(job_id, vis_dirs)
#checkDir(job_id, vis_bk_dirs)
checkDir(job_id, cube_dir)
#checkDir(job_id, out_dir)


obs_list, all_obs = getMyObs(job_id, obs_dir, obs_first, obs_last, num_jobs)
obsId_list = []

print "myobs = \t%s\nvis_dirs = \t%s\nrun_id = \t%s" % (str(obs_list), vis_dirs, run_id)

# Wait on split ...
# done_obs = checkIfAllObsSplitDone(casa_workdir, job_id, run_id, all_obs, timeout = split_tmout)

# this is only for Amazon
done_obs = {}
obslist = glob('%s/*' % vis_dirs)
for obsfile in obslist:
    done_obs[os.path.basename(obsfile)] = 1

vis_dirs_cube = []
for obsId in done_obs.keys():
    vis_dirs_cube.append('%s/%s/' % (vis_dirs, obsId))

do_cube(vis_dirs_cube, cube_dir, freq_min, freq_max, freq_step, freq_width, job_id, num_jobs, debug)

    # Done
