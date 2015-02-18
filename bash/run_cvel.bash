#  _   _  ___ _____ _____
# | \ | |/ _ \_   _| ____|
# |  \| | | | || | |  _|
# | |\  | |_| || | | |___
# |_| \_|\___/ |_| |_____|
#
# The disk setup is done in the setup_disks.bash script
#
# When this is run as a user data start up script is is run as root - BE CAREFUL!!!

# Run the cvel pipeline
##### runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_cvel.sh min_freq max_freq' #####
{0}

# Copy files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_cvel_output.py -p 2 {1}'

# Copy log files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_log_files.py -p 3 CVEL-logs/{1}'

# Unattach the volume and delete it
umount /dev/xvdf
sleep 10
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/delete_volumes.py {2}'

# Terminate
shutdown -h now
