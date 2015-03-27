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
Post process the sqlite database
"""
import argparse
import csv
import logging
from os.path import exists, join
from sqlalchemy import create_engine, Table, Column, Float, Integer, MetaData, String
import sqlite3

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)-15s:' + logging.BASIC_FORMAT)

TRACE_METADATA = MetaData()
LOG_DETAILS = Table(
    'log_details',
    TRACE_METADATA,
    Column('log_details_id', Integer, primary_key=True),
    Column('pid', Integer, index=True, nullable=False),
    Column('timestamp', String(40), index=True, nullable=False),
    Column('state', String(2), nullable=False),
    Column('utime', Integer, nullable=False),
    Column('stime', Integer, nullable=False),
    Column('cutime', Integer, nullable=False),
    Column('cstime', Integer, nullable=False),
    Column('priority', Integer, nullable=False),
    Column('nice', Integer, nullable=False),
    Column('num_threads', Integer, nullable=False),
    Column('vsize', Integer, nullable=False),
    Column('rss', Integer, nullable=False),
    Column('blkio_ticks', Integer, nullable=False),
    Column('rchar', Integer, nullable=False),
    Column('wchar', Integer, nullable=False),
    Column('syscr', Integer, nullable=False),
    Column('syscw', Integer, nullable=False),
    Column('read_bytes', Integer, nullable=False),
    Column('write_bytes', Integer, nullable=False),
    Column('cancelled_write_bytes', Integer, nullable=False),
    sqlite_autoincrement=True
)
STAT_DETAILS = Table(
    'stat_details',
    TRACE_METADATA,
    Column('stat_details_id', Integer, primary_key=True),
    Column('timestamp', String(40), index=True, nullable=False),
    Column('user', Integer, nullable=False),
    Column('nice', Integer, nullable=False),
    Column('system', Integer, nullable=False),
    Column('idle', Integer, nullable=False),
    Column('iowait', Integer, nullable=False),
    Column('irq', Integer, nullable=False),
    Column('softirq', Integer, nullable=False),
    Column('steal', Integer, nullable=False),
    Column('guest', Integer, nullable=False),
    Column('guest_nice', Integer, nullable=False),
    sqlite_autoincrement=True
)
PROCESS_DETAILS = Table(
    'process_details',
    TRACE_METADATA,
    Column('process_details_id', Integer, primary_key=True),
    Column('pid', Integer, index=True, nullable=False),
    Column('ppid', Integer, nullable=False),
    Column('name', String(256), nullable=False),
    Column('cmd_line', String(2000), nullable=False),
    Column('create_time', Float, nullable=False),
    sqlite_autoincrement=True
)
TRACE_DETAILS = Table(
    'trace_details',
    TRACE_METADATA,
    Column('start_time', String(40), nullable=False),
    Column('cmd_line', String(2000), nullable=False),
    Column('sample_rate', Float, nullable=False),
    Column('tick', Integer, nullable=False),
    Column('page_size', Integer, nullable=False)
)
POST_DETAILS = Table(
    'post_details',
    TRACE_METADATA,
    Column('post_details_id', Integer, primary_key=True),
    Column('pid', Integer, index=True, nullable=False),
    Column('timestamp', Float, index=True, nullable=False),
    Column('total_cpu', Float, nullable=False),
    Column('kernel_cpu', Float, nullable=False),
    Column('vm', Float, nullable=False),
    Column('rss', Float, nullable=False),
    Column('iops', Float, nullable=False),
    Column('bytes_sec', Float, nullable=False),
    Column('read_bytes', Integer, nullable=False),
    Column('write_bytes', Integer, nullable=False),
    Column('read_count', Integer, nullable=False),
    Column('write_count', Integer, nullable=False),
    Column('blkio_wait', Float, nullable=False),
    sqlite_autoincrement=True
)


def get_pids(connection):
    pids = []
    for process_details in connection.execute(PROCESS_DETAILS.select()):
        pids.append(process_details[PROCESS_DETAILS.c.pid])
    return pids


def calculate_values(connection, pid, details):
    insert = POST_DETAILS.insert()
    sample_rate = details[0]
    tick = details[1]
    page_size = details[2]
    read_count1 = None
    write_count1 = None
    read_bytes1 = None
    write_bytes1 = None
    blkio_ticks1 = None
    total_cpu1 = None
    kernel_cpu1 = None
    ios1 = None
    io_bytes1 = None

    for log_details in connection.execute(LOG_DETAILS.select().where(LOG_DETAILS.c.pid == pid).order_by(LOG_DETAILS.c.timestamp)):
        utime2 = log_details[LOG_DETAILS.c.utime]
        stime2 = log_details[LOG_DETAILS.c.stime]
        read_count2 = log_details[LOG_DETAILS.c.read_count]
        write_count2 = log_details[LOG_DETAILS.c.write_count]
        read_bytes2 = log_details[LOG_DETAILS.c.read_bytes]
        write_bytes2 = log_details[LOG_DETAILS.c.write_bytes]
        blkio_ticks2 = log_details[LOG_DETAILS.c.blkio_ticks]

        total_cpu2 = utime2 + stime2
        kernel_cpu2 = stime2
        ios2 = read_count2 + write_count2
        io_bytes2 = read_bytes2 + write_bytes2
        if total_cpu1 is not None:
            total_cpu = int(100.0 * (total_cpu2 - total_cpu1) / tick / sample_rate)
            kernel_cpu = int(100.0 * (kernel_cpu2 - kernel_cpu1) / tick / sample_rate)
            iops = ios2 - ios1
            io_bytes = io_bytes2 - io_bytes1
            blkio_wait = float(blkio_ticks2 - blkio_ticks1) / tick / sample_rate

            connection.execute(
                insert,
                pid=pid,
                timestamp=log_details[LOG_DETAILS.c.timestamp],
                total_cpu=total_cpu,
                kernel_cpu=kernel_cpu,
                vm=log_details[LOG_DETAILS.c.vsize],
                rss=log_details[LOG_DETAILS.c.rss] * page_size,
                iops=iops,
                bytes_sec=io_bytes,
                read_bytes=read_bytes2 - read_bytes1,
                write_bytes=write_bytes2 - write_bytes1,
                blkio_wait=blkio_wait,
                read_count=read_count2 - read_count1,
                write_count=write_count2 - write_count1
            )

        read_count1 = read_count2
        write_count1 = write_count2
        read_bytes1 = read_bytes2
        write_bytes1 = write_bytes2
        blkio_ticks1 = blkio_ticks2
        total_cpu1 = total_cpu2
        kernel_cpu1 = kernel_cpu2
        ios1 = ios2
        io_bytes1 = io_bytes2


def get_details(connection):
    trace_details = connection.execute(TRACE_DETAILS.select()).first()
    return [trace_details[TRACE_DETAILS.c.sample_rate],
            trace_details[TRACE_DETAILS.c.tick],
            trace_details[TRACE_DETAILS.c.page_size]]


def load_csv(database, csv_files):
    for csv_file in csv_files:
        sql = None
        if csv_file.endswith('_trace_details.csv'):
            sql = '''INSERT INTO trace_details (start_time, cmd_line, sample_rate, tick, page_size)
VALUES (:start_time, :cmd_line, :sample_rate, :tick, :page_size)'''
        elif csv_file.endswith('_log_details.csv'):
            sql = '''INSERT INTO log_details (pid, timestamp, state, utime, stime, cutime, cstime, priority, nice, num_threads, vsize, rss, blkio_ticks, rchar, wchar, syscr, syscw, read_bytes, write_bytes, cancelled_write_bytes)
VALUES (:pid, :timestamp, :state, :utime, :stime, :cutime, :cstime, :priority, :nice, :num_threads, :vsize, :rss, :blkio_ticks, :rchar, :wchar, :syscr, :syscw, :read_bytes, :write_bytes, :cancelled_write_bytes)'''
        elif csv_file.endswith('_stat_details.csv'):
            sql = '''INSERT INTO stat_details (timestamp, user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice)
VALUES (:timestamp, :user, :nice, :system, :idle, :iowait, :irq, :softirq, :steal, :guest, :guest_nice)'''
        elif csv_file.endswith('_process_details.csv'):
            sql = '''INSERT INTO process_details (pid, ppid, name, cmd_line, create_time)
VALUES (:pid, :ppid, :name, :cmd_line, :create_time)'''

        if sql is not None:
            with open(csv_file, 'rt') as csv_file1:
                csv_reader = csv.DictReader(csv_file1)

                with sqlite3.connect(database) as connection:
                    cursor = connection.cursor()
                    cursor.executemany(sql, csv_reader)


def post_process_database(database, csv_files):
    # Create the database
    engine = create_engine('sqlite:///{0}'.format(database))
    connection = engine.connect()
    TRACE_METADATA.create_all(connection)
    #connection.close()

    # Load the CSV file
    load_csv(database, csv_files)

    # Get the details we need
    #engine = create_engine('sqlite:///{0}'.format(database))
    #connection = engine.connect()
    pids = get_pids(connection)
    details = get_details(connection)

    for pid in pids:
        with connection.begin():
            calculate_values(connection, pid, details)

    connection.close()


def files_exist(csv_files):
    for csv_file in csv_files:
        if not exists(csv_file):
            return False

    return True


def post_process(csv_stems, database_directory):
    for csv_stem in csv_stems:
        database = join(database_directory, csv_stem + '.db')
        csv_files = [
            csv_stem + '_log_details.csv',
            csv_stem + '_process_details.csv',
            csv_stem + '_stat_details.csv',
            csv_stem + '_trace_details.csv']
        if exists(database):
            LOG.error('The database {0} already exists.'.format(database))
        elif not files_exist(csv_files):
            LOG.error('Not all the CSV files exists: {0}.'.format(csv_files))
        else:
            post_process_database(database, csv_files)


def main():
    parser = argparse.ArgumentParser('Post process the sqlite database')
    parser.add_argument('-d', '--dir', default='/tmp', help='the directory to create the sqlite database in')
    parser.add_argument('csv_files', nargs='+', help='the stem of csv files to be processed')
    args = vars(parser.parse_args())

    post_process(args['csv_files'], args['dir'])


if __name__ == "__main__":
    main()
