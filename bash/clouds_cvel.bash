#  _   _  ___ _____ _____
# | \ | |/ _ \_   _| ____|
# |  \| | | | || | |  _|
# | |\  | |_| || | | |___
# |_| \_|\___/ |_| |_____|
#
# The disk setup is done in the setup_disks.bash script
#
# When this is run as a user data start up script it is run as root - BE CAREFUL!!!

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

rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm

# Install the latest versions of the Python libraries and pull the latest code
pip2.7 install {4}

cd /home/ec2-user
rm -rf /home/ec2-user/chiles_pipeline
git clone -b msc_ec2-user --single-branch https://github.com/nebgor/chiles_pipeline.git
# fyi: git grep -l 'ec2-user' | xargs sed -i 's/ec2-user/centos/g'
cd /home/ec2-user/chiles_pipeline
git pull


# Run the cvel pipeline
##### runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_cvel.sh min_freq max_freq' #####
##### runuser -l ec2-user -c 'python2.7 /home/ec2-user/chiles_pipeline/python/copy_cvel_output.py vis_ obs-id' #####

{0}

# Log the disk usage
df -h

# Copy log files to S3

python2.7 /home/ec2-user/chiles_pipeline/python/copy_log_files.py -p 3 CVEL-logs/{1}/{2}-{3}

## Unattach the volume and delete it
umount /dev/xvdf
sleep 10
# python2.7 /home/ec2-user/chiles_pipeline/python/delete_volumes.py {2} # this was decoupled from here.

# Terminate (the volume will be deleted too..)
shutdown -h now
