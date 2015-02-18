#  _   _  ___ _____ _____
# | \ | |/ _ \_   _| ____|
# |  \| | | | || | |  _|
# | |\  | |_| || | | |___
# |_| \_|\___/ |_| |_____|
#
# The disk setup is done in the setup_disks.bash script
#
# When this is run as a user data start up script is is run as root - BE CAREFUL!!!

# Copy files from S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_makecube_input.py -p 4'

# Run the make pipeline
runuser -l ec2-user -c 'bash -vx /home/ec2-user/chiles_pipeline/bash/start_makecube.sh {0}'

# Copy files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_makecube_output.py {0}'

# Copy log files to S3
runuser -l ec2-user -c 'python /home/ec2-user/chiles_pipeline/python/copy_log_files.py -p 3 IMGCONCAT-logs/{0}'

# Terminate
shutdown -h now
