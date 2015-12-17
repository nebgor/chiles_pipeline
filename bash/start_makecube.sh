#!/bin/sh

export IMAGE_NAME=$1
export CH_CASA_WORK_DIR=$HOME/Chiles/casa_work_dir

mkdir -p ${CH_CASA_WORK_DIR}
cd ${CH_CASA_WORK_DIR}

# point to casapy installation
export PATH=$PATH:/home/centos/casapy-42.2.30986-1-64b/bin
export PYTHONPATH=${PYTHONPATH}:/home/centos/chiles_pipeline/python
export HOME=/home/centos
export USER=root

casapy --nologger  --log2term --logfile casapy.log  -c /home/centos/chiles_pipeline/python/image_concat.py
