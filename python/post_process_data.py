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
from os.path import exists
from sqlalchemy import create_engine, Table, Column, Float, Integer
from launch_trace2 import TRACE_METADATA, PROCESS_DETAILS, TRACE_DETAILS, LOG_DETAILS

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
        cutime2 = log_details[LOG_DETAILS.c.cutime]
        cstime2 = log_details[LOG_DETAILS.c.cstime]
        read_count2 = log_details[LOG_DETAILS.c.read_count]
        write_count2 = log_details[LOG_DETAILS.c.write_count]
        read_bytes2 = log_details[LOG_DETAILS.c.read_bytes]
        write_bytes2 = log_details[LOG_DETAILS.c.write_bytes]
        blkio_ticks2 = log_details[LOG_DETAILS.c.blkio_ticks]

        total_cpu2 = utime2 + stime2 + cutime2 + cstime2
        kernel_cpu2 = stime2 + cstime2
        ios2 = read_count2 + write_count2
        io_bytes2 = read_bytes2 + write_bytes2
        if total_cpu1 is not None:
            total_cpu = int(100.0 * (total_cpu2 - total_cpu1) / tick / sample_rate)
            kernel_cpu = int(100.0 * (kernel_cpu2 - kernel_cpu1) / tick / sample_rate)
            iops = ios2 - ios1
            io_bytes = io_bytes2 - io_bytes1
            blkio_wait =  (blkio_ticks2 - blkio_ticks1) * tick * sample_rate

            connection.execute(
                insert,
                pid=pid,
                timestamp=log_details[LOG_DETAILS.c.timestamp],
                total_cpu=total_cpu,
                kernel_cpu=kernel_cpu,
                vm=log_details[LOG_DETAILS.c.vsize],
                rss=log_details[LOG_DETAILS.c.rss] * page_size,
                iops= iops,
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
            trace_details[TRACE_DETAILS.c.page_size]
            ]


def post_process_database(database):
    engine = create_engine('sqlite:///{0}'.format(database))
    POST_DETAILS.drop(engine, checkfirst=True)
    POST_DETAILS.create(engine, checkfirst=False)

    connection = engine.connect()
    pids = get_pids(connection)
    details = get_details(connection)

    for pid in pids:
        transaction = connection.begin()
        calculate_values(connection, pid, details)
        transaction.commit()

    connection.close()

def post_process(databases):
    for database in databases:
        if exists(database):
            post_process_database(database)


def main():
    parser = argparse.ArgumentParser('Post process the sqlite database')
    parser.add_argument('databases', nargs='+', help='the databases to be processed')
    args = vars(parser.parse_args())

    post_process(args['databases'])

if __name__ == "__main__":
    main()
