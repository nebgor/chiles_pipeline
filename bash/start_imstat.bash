#!/bin/bash
export CH_FREQ_MIN=$1 # MHz -- must be int (could be float if required, but makecube would need changing)
export CH_FREQ_MAX=$2 # MHz -- must be int
export CLEAN_NUMBER=$3

casapy --nologger  --log2term --logfile casapy.log  -c /home/ec2-user/chiles_pipeline/python/casapy_run_imstat.py
