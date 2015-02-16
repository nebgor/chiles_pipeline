"""
Taken from makecube.py extracting the loop over clean

This module should run together with the casapy: e.g. casapy --nologger -c loop_clean.py
"""
import fnmatch
import os
from os.path import join
from echo import dump_all
from makecube_defines import check_dir, cube_dir, vis_dirs, run_id, do_cube, freq_min, freq_max, freq_step, freq_width, job_id, num_jobs, debug

check_dir(cube_dir)

print '''
vis_dirs = {0}
run_id   = {1}'''.format(vis_dirs, run_id)

vis_dirs_cube = []
for root, dir_names, filenames in os.walk(vis_dirs):
    for match in fnmatch.filter(dir_names, 'vis_*'):
        vis_dirs_cube.append('{0}'.format(join(root, match)))


dump_all()
do_cube(vis_dirs_cube, cube_dir, freq_min, freq_max, freq_step, freq_width)

# Done
