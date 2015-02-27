#  _   _  ___ _____ _____
# | \ | |/ _ \_   _| ____|
# |  \| | | | || | |  _|
# | |\  | |_| || | | |___
# |_| \_|\___/ |_| |_____|
#
# The disk setup is done in the setup_disks.bash script
#
# When this is run as a user data start up script it is run as root - BE CAREFUL!!!

# Do we have an EBS volume mount and format it
if [ -b '/dev/xvdf' ]; then
    echo 'Detected EBS'
    mkfs.ext4 /dev/xvdf
    mkdir -p /mnt/input
    mount -t ext4 -o noatime /dev/xvdf /mnt/input
else
    echo 'No EBS volume'
    mkdir -p /mnt/output/input
    chmod -R 0777 /mnt/output/input
    ln -s /mnt/output/input /mnt/input
fi

# Install the latest versions of the Python libraries and pull the latest code
pip install {1}
cd /home/ec2-user/chiles_pipeline
runuser -l ec2-user -c '(cd /home/ec2-user/chiles_pipeline ; git pull)'

# Copy files from S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_makecube_input.py -p 4'

# Run the make pipeline
runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_makecube.sh {0}'

# Copy files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_makecube_output.py {0}'

# Copy log files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_log_files.py -p 3 IMGCONCAT-logs/{0}'

# Terminate
#shutdown -h now
