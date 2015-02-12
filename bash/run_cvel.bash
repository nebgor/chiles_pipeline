#!/bin/bash -vx
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
  sleep 30
done

# Now mount the data disk
mkdir -p /mnt/Data/data1
mount /dev/xvdf /mnt/Data/data1
chmod -R oug+r /mnt/Data/data1

# Wait for the boto file to be created
while [ ! -f "/home/ec2-user/.boto" ]; do
  echo Sleeping
  sleep 30
done

# Run the cvel pipeline
##### runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_cvel.sh min_freq max_freq' #####
{0}

# Copy files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_cvel_output.py -p 3 {1}'

# Unattach the volume and delete it
umount /dev/xvdf
sleep 10
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/delete_volume {2}'

# Terminate
#shutdown -h now
