"""
Taken from makecube.py extracting the final combination of cubes

This module should run together with the casapy: e.g. casapy --logfile casapy.log -c make_finalcube.py
"""

execfile('/home/ec2-user/chiles_pipeline/python/makecube_defines.py')

check_dir(job_id, out_dir)


obs_list, all_obs = getMyObs(job_id, obs_dir, obs_first, obs_last, num_jobs)
obsId_list = []

print "myobs = \t%s\nvis_dirs = \t%s\nrun_id = \t%s" % (str(obs_list), vis_dirs, run_id)

# Wait on clean ...

if (job_id == 0): # only the first job will do the final concatenation
    combineAllCubes(cube_dir,outname,freq_min,freq_max,freq_step,casa_workdir,
                    run_id, debug, timeout = clean_tmout)

