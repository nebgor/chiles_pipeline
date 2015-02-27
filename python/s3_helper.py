#
#    (c) UWA, The University of Western Australia
#    M468/35 Stirling Hwy
#    Perth WA 6009
#    Australia
#
#    Copyright by UWA, 2012-2015
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
A helper for S3
"""
from os.path import join, expanduser, exists
import socket
import tarfile
import time
import math
import mimetypes
from multiprocessing import Pool
import os

import boto
from boto.s3.key import Key
import multiprocessing
from cStringIO import StringIO

from common import LOGGER, Consumer

from file_chunk_io import FileChunkIO


def upload_part(bucket_name, multipart_id, part_num, source_path, offset, bytes_to_copy, amount_of_retries=10):
    """
    Uploads a part with retries.  It is outside the class to get pickling to work properly
    """
    def _upload(retries_left=amount_of_retries):
        try:
            LOGGER.info('Start uploading part #%d ...' % part_num)
            conn = boto.connect_s3()
            bucket = conn.get_bucket(bucket_name)
            for mp in bucket.get_all_multipart_uploads():
                if mp.id == multipart_id:
                    with FileChunkIO(source_path, 'r', offset=offset, bytes=bytes_to_copy) as fp:
                        mp.upload_part_from_file(fp=fp, part_num=part_num)
                    break
        except Exception, exc:
            if retries_left:
                _upload(retries_left=retries_left - 1)
            else:
                LOGGER.info('... Failed uploading part #%d' % part_num)
                raise exc
        else:
            LOGGER.info('... Uploaded part #%d' % part_num)

    _upload()


class S3Helper:
    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None):
        """
        Get an S3 connection
        :return:
        """
        if aws_access_key_id is not None and aws_secret_access_key is not None:
            LOGGER.info("Using user provided keys")
            self.s3_connection = boto.connect_s3(aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
        elif exists(join(expanduser('~'), '.aws/credentials')):
            # This relies on a ~/.aws/credentials file holding the '<aws access key>', '<aws secret key>'
            LOGGER.info("Using ~/.aws/credentials")
            self.s3_connection = boto.connect_s3(profile_name='chiles')
        else:
            # This relies on a ~/.boto or /etc/boto.cfg file holding the '<aws access key>', '<aws secret key>'
            LOGGER.info("Using ~/.boto or /etc/boto.cfg")
            self.s3_connection = boto.connect_s3()

    def get_bucket(self, bucket_name):
        """
        Get a S3 bucket

        :param bucket_name:
        :return:
        """
        return self.s3_connection.get_bucket(bucket_name)

    def add_file_to_bucket(self, bucket_name, key_name, filename, reduced_redundancy=True):
        """
        Add file to a bucket

        :param bucket_name:
        :param key_name:
        :param filename:
        """
        LOGGER.info('bucket_name: {0}, key_name: {1}, filename: {2}, reduced_redundancy: {3}'.format(bucket_name, key_name, filename, reduced_redundancy))
        retry_count = 0
        done = False
        while retry_count < 3 and not done:
            try:
                bucket = self.get_bucket(bucket_name)
                key = Key(bucket)
                key.key = key_name
                key.set_contents_from_filename(filename, reduced_redundancy=reduced_redundancy)
                done = True
            except socket.error:
                LOGGER.exception('Error')
                retry_count += 1
                time.sleep(10)

    def get_file_from_bucket(self, bucket_name, key_name, file_name):
        """
        Get a file from S3 into a local file

        :param bucket_name:
        :param key_name:
        :param file_name:
        :return:
        """
        bucket = self.get_bucket(bucket_name)
        key = Key(bucket)
        key.key = key_name
        key.get_contents_to_filename(file_name)

    def add_file_to_bucket_multipart(self, bucket_name, key_name, source_path, parallel_processes=4, reduced_redundancy=True):
        """
        Parallel multipart upload.
        """
        LOGGER.info('bucket_name: {0}, key_name: {1}, filename: {2}, parallel_processes: {3}, reduced_redundancy: {4}'.format(
            bucket_name, key_name, source_path, parallel_processes, reduced_redundancy))
        bucket = self.get_bucket(bucket_name)

        headers = {'Content-Type': mimetypes.guess_type(key_name)[0] or 'application/octet-stream'}
        mp = bucket.initiate_multipart_upload(key_name, headers=headers, reduced_redundancy=reduced_redundancy)

        source_size = os.stat(source_path).st_size
        bytes_per_chunk = max(int(math.sqrt(5242880) * math.sqrt(source_size)), 5242880)
        chunk_amount = int(math.ceil(source_size / float(bytes_per_chunk)))
        LOGGER.info('bytes_per_chunk: {0}, chunk_amount: {1}'.format(bytes_per_chunk, chunk_amount))

        pool = Pool(processes=parallel_processes)
        for i in range(chunk_amount):
            offset = i * bytes_per_chunk
            remaining_bytes = source_size - offset
            bytes_to_copy = min([bytes_per_chunk, remaining_bytes])
            part_num = i + 1
            pool.apply_async(upload_part, [bucket_name, mp.id, part_num, source_path, offset, bytes_to_copy])
        pool.close()
        pool.join()

        if len(mp.get_all_parts()) == chunk_amount:
            mp.complete_upload()
        else:
            mp.cancel_upload()

    def add_tar_to_bucket_multipart(self, bucket_name, key_name, source_path, gzip=True, parallel_processes=4, reduced_redundancy=True):
        """
        Parallel multipart upload.
        """
        LOGGER.info(
            'bucket_name: {0}, key_name: {1}, source_path: {2}, parallel_processes: {3}, reduced_redundancy: {4}'.format(
                bucket_name,
                key_name,
                source_path,
                parallel_processes,
                reduced_redundancy
            )
        )
        bucket = self.get_bucket(bucket_name)

        task_queue = multiprocessing.JoinableQueue()

        # Start the consumers
        for x in range(parallel_processes):
            consumer = Consumer(task_queue)
            consumer.start()

        headers = {'Content-Type': mimetypes.guess_type(key_name)[0] or 'application/octet-stream'}
        mp = bucket.initiate_multipart_upload(key_name, headers=headers, reduced_redundancy=reduced_redundancy)
        s3_feeder = S3Feeder(task_queue, mp)

        if gzip:
            mode = "w|gz"
        else:
            mode = "w|"
        tar = tarfile.open(mode=mode, fileobj=s3_feeder)

        complete = True
        # noinspection PyBroadException
        try:
            for entry in os.listdir(source_path):
                full_filename = join(source_path, entry)
                tar.add(full_filename, arcname=entry)

            tar.close()
            s3_feeder.close()
        except Exception:
            complete = False

        # Add a poison pill to shut things down
        for x in range(parallel_processes):
            task_queue.put(None)

        # Wait for the queue to terminate
        task_queue.join()

        # Finish the upload
        if complete:
            mp.complete_upload()
        else:
            mp.cancel_upload()


class MultipartTask(object):
    def __init__(self, data, part_num, multipart_upload):
        self._data = data
        self._part_num = part_num
        self._multipart_upload = multipart_upload

    def __call__(self):
        # noinspection PyBroadException
        try:
            LOGGER.info('Writing part {0} - {1} bytes'.format(self._part_num, len(self._data)))
            fp = StringIO(self._data)
            self._multipart_upload.upload_part_from_file(fp=fp, part_num=self._part_num)
        except Exception:
            LOGGER.exception('Exception executing the task')


class S3Feeder:
    def __init__(self, queue, multipart_upload):
        self._buffer = ""
        self._bufsize = 5242880
        self._part_num = 1
        self._queue = queue
        self._multipart_upload = multipart_upload
        self._closed = False

    def write(self, data):
        self._buffer += data
        while len(self._buffer) > self._bufsize:
            self._queue.put(MultipartTask(self._buffer[:self._bufsize], self._part_num, self._multipart_upload))
            self._part_num += 1
            self._buffer = self._buffer[self._bufsize:]

    def close(self):
        if not self._closed:
            self._queue.put(MultipartTask(self._buffer[:self._bufsize], self._part_num, self._multipart_upload))
            self._part_num += 1
            self._closed = True
