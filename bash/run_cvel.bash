#!/bin/bash -ve
# When this is run as a user data start up script is is run as root - BE CAREFUL!!!
# Setup the ephemeral disk
if [ -b "/dev/xvdb" ]; then
  if mountpoint -q "/media/ephemeral0" ; then
    # The ephemeral disk is mounted on /media/ephemeral0
    rm -f /mnt/output
    ln -s /media/ephemeral0 /mnt/output
  else
    mkdir -p /mnt/output
    mkfs.ext4 /dev/xvdb
    mount /dev/xvdb /mnt/output
  fi
fi
chmod oug+wrx /mnt/output


# As we might need to wait for the mount point to arrive as it can only be attached
# after the instance is running
sleep 10
while [ ! -b "/dev/xvdf" ]; do
  echo Sleeping
  sleep 10
done

# Now mount the data disk
mkdir -p /mnt/Data/data1
mount /dev/xvdf /mnt/Data/data1
chmod -R oug+r /mnt/Data/data1

# Make sure the code area is up to date and is run by ec2-user not root
cd /home/ec2-user/chiles_pipeline
runuser -l ec2-user -c 'git pull'

# CHEN - You bits go here :-)
cd /home/ec2-user
runuser -l ec2-user -c 'sh ~/chiles_pipeline/bash/start_cvel.sh'

# Copy files to S3
# TODO - when I see what the output looks like

# Terminate
#shutdown -h now
