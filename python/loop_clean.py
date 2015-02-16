"""
Taken from makecube.py extracting the loop over clean

This module should run together with the casapy: e.g. casapy --nologger -c loop_clean.py
"""
from glob import glob
import os
from makecube_defines import check_dir, cube_dir, obs_dir, get_my_obs, vis_dirs, run_id, do_cube, freq_min, freq_max, freq_step, freq_width, job_id, num_jobs, debug

check_dir(cube_dir)

print '''
vis_dirs = {0}
run_id   = {1}'''.format(vis_dirs, run_id)

done_obs = {}
obslist = glob('%s/*' % vis_dirs)
for obsfile in obslist:
    done_obs[os.path.basename(obsfile)] = 1

vis_dirs_cube = []
for obsId in done_obs.keys():
    vis_dirs_cube.append('%s/%s/' % (vis_dirs, obsId))

do_cube(vis_dirs_cube, cube_dir, freq_min, freq_max, freq_step, freq_width, job_id, num_jobs, debug)

# Done
