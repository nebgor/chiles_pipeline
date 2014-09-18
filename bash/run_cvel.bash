#!/bin/bash

# As we might need to wait for the mount point to arrive as it can only be attached
# after the instance is running
sleep 10
while [ ! -b "/dev/xvdf" ]; do
  echo Sleeping
  sleep 10
done

# Mount ephemeral disk
if [ -b "/dev/xvdb" ]; then
  sudo mkdir -p /mnt/data2
  sudo mount /dev/xvdb /mnt/data2
  sudo mkfs.ext4 /dev/data2
  sudo chmod oug+rwx /mnt/data2
fi

# make sure the code area is up to date
cd chiles_pipeline
git pull

# CHEN - You bits go here :-)
cd ~


# Copy files to S3
# TODO - when I see what the output looks like

# Terminate
#shutdown
