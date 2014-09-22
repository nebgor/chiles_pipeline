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

# Make sure the code area is up to date and is run by ec2-user not root
runuser -l ec2-user -c 'cd /home/ec2-user/chiles_pipeline ; git pull'

# Copy files from S3
#runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_clean_input.py {0}'

# Run the cvel pipeline
runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_clean.sh {0} 0 1'

# Copy files to S3
#runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_clean_output.py'

# Terminate
#shutdown -h now
