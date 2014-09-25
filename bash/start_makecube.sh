#!/bin/sh

export IMAGE_NAME=$1
export CH_CASA_WORK_DIR=/mnt/output/Chiles/casa_work_dir

mkdir -p $CH_CASA_WORK_DIR
cd $CH_CASA_WORK_DIR

# point to casapy installation
export PATH=$PATH:/home/ec2-user/casapy-42.2.30986-1-64b/bin
casapy --nologger  --log2term --logfile casapy.log  -c /home/ec2-user/chiles_pipeline/python/image_concat.py
