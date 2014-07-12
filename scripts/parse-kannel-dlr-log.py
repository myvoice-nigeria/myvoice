#!/usr/bin/env python
# Usage:
# python parse-kannel-dlr-logs.py bearerbox.log output.csv

import re
import datetime
import csv
import sys

LOOK_PAT = re.compile('([-0-9 :]+).+Looking for DLR.+smsc=([-\w]+).+ts=([.\w]+),.+')
ADDING_PAT = re.compile('([-0-9- :]+).+Adding DLR.+smsc=([-\w]+).+ts=([.\w]+),.+')

dlr = {}
with open(sys.argv[1]) as f:
    line = f.readline()
    while line:
        look = LOOK_PAT.match(line)
        if look:
            time, smsc, msgid = look.groups()
            if msgid in dlr:
                time = datetime.datetime.strptime(time.strip(), "%Y-%m-%d %H:%M:%S")
                dlr[msgid]['delivery_time'] = time
                dlr[msgid]['time_diff'] = dlr[msgid]['delivery_time'] - dlr[msgid]['send_time']
        adding = ADDING_PAT.match(line)
        if adding:
            time, smsc, msgid = adding.groups()
            time = datetime.datetime.strptime(time.strip(), "%Y-%m-%d %H:%M:%S")
            dlr[msgid] = {'send_time': time, 'smsc': smsc}
        line = f.readline()

w = csv.writer(open(sys.argv[2], 'w'))
w.writerow(['send_time', 'delivery_time', 'time_diff', 'smsc', 'msgid'])
for k, v in dlr.iteritems():
    row = [
        v['send_time'].strftime('%Y-%m-%d %H:%M:%S'),
        v['delivery_time'].strftime('%Y-%m-%d %H:%M:%S') if 'delivery_time' in v else '',
        v['time_diff'].total_seconds() if 'time_diff' in v else '',
        v['smsc'],
        k,
    ]
    w.writerow(row)
