#!/bin/bash
# When this is run as a user data start up script is is run as root - BE CAREFUL!!!
# Setup the ephemeral disk
if [ -b "/dev/xvdb" ]; then
  if mountpoint -q "/media/ephemeral0" ; then
    # The ephemeral disk is mounted on /media/ephemeral0
    rm -f /mnt/data2
    ln -s /media/ephemeral0 /mnt/data2
  else
    mkdir -p /mnt/data2
    mkfs.ext4 /dev/xvdb
    mount /dev/xvdb /mnt/data2
  fi
fi
chmod oug+wrx /mnt/data2

# As we might need to wait for the mount point to arrive as it can only be attached
# after the instance is running
sleep 10
while [ ! -b "/dev/xvdf" ]; do
  echo Sleeping
  sleep 10
done

# Now mount the data disk
mkdir -p /mnt/data1
mount /dev/xvdf /mnt/data1

# make sure the code area is up to date
cd chiles_pipeline
runuser -l ec2-user git pull

# CHEN - You bits go here :-)
cd ~
runuser -l ec2-user echo "Hello World!"

# Copy files to S3
# TODO - when I see what the output looks like

# Terminate
#shutdown -h now
