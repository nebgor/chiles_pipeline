"""
Taken from makecube.py extracting the loop over cvel

This module should run together with the casapy: e.g. casapy --nologger -c loop_cvel.py
"""
import os
from echo import dump_all
from makecube_defines import INPUT_VIS_SUFFIX, check_dir, get_my_obs, vis_bk_dirs, vis_dirs, obs_dir, execCmd, do_cvel, freq_max, freq_min, freq_step, freq_width, spec_window, run_id


print 'test'+INPUT_VIS_SUFFIX
# loop through selected obs and cvel. Uses obId to only do subset of possible

check_dir(vis_dirs)
check_dir(vis_bk_dirs)

obs_list = get_my_obs(obs_dir)
dump_all()

for obs in obs_list:
    infile_dir = os.path.join(obs_dir, obs)

    infile = None
    for ff in os.listdir(infile_dir):
        if ff.endswith(INPUT_VIS_SUFFIX):
            infile = '%s/%s' % (infile_dir, ff)
    if not infile:
        print 'No measurementSet file found under %s' % infile_dir
        continue

    obsId = os.path.basename(infile_dir).replace('_FINAL_PRODUCTS', '')
    outdir = '%s/%s/' % (vis_dirs, obsId)
    backup_dir = '%s/%s/' % (vis_bk_dirs, obsId)

    dump_all()
    do_cvel(infile, outdir, backup_dir, freq_min, freq_max, freq_step, freq_width, spec_window, obsId)
