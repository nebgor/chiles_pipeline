#
#    (c) UWA, The University of Western Australia
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA, 2012-2014
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#
"""
Copy the clean output
"""
import argparse
import os
from os.path import join, isdir, basename
import sys

from common import make_safe_filename, make_tarfile, LOGGER
from settings_file import CHILES_BUCKET_NAME, CHILES_IMGCONCAT_OUTPUT
from s3_helper import S3Helper

LOGGER.info('PYTHONPATH = {0}'.format(sys.path))


def copy_files(cube):
    # Look in the output directory
    directory_to_save = join(CHILES_IMGCONCAT_OUTPUT, cube) + '.cube'
    if isdir(directory_to_save):
        LOGGER.info('dir_name: {0}'.format(directory_to_save))
        output_tar_filename = directory_to_save + '.tar.gz'
        # noinspection PyBroadException
        try:
            make_tarfile(output_tar_filename, directory_to_save)

            LOGGER.info('Copying {0} to s3'.format(output_tar_filename))
            s3_helper = S3Helper()
            s3_helper.add_file_to_bucket_multipart(
                CHILES_BUCKET_NAME,
                'IMGCONCAT/{0}' + basename(output_tar_filename),
                output_tar_filename)

            # Clean up
            os.remove(output_tar_filename)
        except Exception:
            LOGGER.exception('Task died')


def main():
    parser = argparse.ArgumentParser('Copy the IMGCONCAT output to the correct place in S3')
    parser.add_argument('cube', help='the cube id')
    args = vars(parser.parse_args())
    cube = make_safe_filename(args['cube'])

    copy_files(cube)

if __name__ == "__main__":
    main()
