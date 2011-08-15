#!/usr/bin/env python

import cgi
import psycopg2
from time import time, ctime
from datetime import date, datetime
import re

conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
c = conn.cursor()

form = cgi.FieldStorage()
bot = 'iawatchbot'
logtype = 'logs'
t = None
d = None
if form.getlist("bot"):
    bot = form.getlist("bot")[0]
if form.getlist("logtype"):
    logtype = form.getlist("logtype")[0]
if form.getlist("time"):
    t = form.getlist("time")[0]
if form.getlist("date"):
    d = form.getlist("date")[0]

now = time()
midnight = now - now % 86400

print "Content-type: text/html; charset=UTF-8\n\n"
print "<html><body><title>Bot Logs</title>"

if t is not None:
    c.execute("select * from logs where time = %s and logtype = %s and bot = %s", (t, logtype, bot))
    output = c.fetchone()[3]
    output = re.sub("\n", "<br>", output)
    print output

if d is None and t is None:
    for x in range(30):
        seconds = midnight - x * 86400
	today = ctime(seconds)
        next = ctime(seconds + 86400)
	dt = datetime.strptime(today, "%a %b %d %H:%M:%S %Y")
        dt2 = datetime.strptime(next, "%a %b %d %H:%M:%S %Y")
        c.execute('select * from logs where time >= %s and time <= %s and bot = %s and logtype = %s', (dt, dt2, bot, logtype))
        if not c.fetchall():
            continue
	day = dt.strftime("%b %d, %Y")
	print '<a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?date=%s&bot=%s&logtype=%s">%s</a>' % (seconds, bot, logtype, day)
	print "<br>"

if d is not None and t is None:
    first = datetime.strptime(ctime(float(d)), "%a %b %d %H:%M:%S %Y")
    last = datetime.strptime(ctime(float(d) + 86400), "%a %b %d %H:%M:%S %Y")
    c.execute("select * from logs where time >= %s and time <= %s and bot = %s and logtype = %s", (first, last, bot, logtype))
    logs = c.fetchall()
    logs.sort()
    logs.reverse()
    for log in logs:
        print '<a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?bot=%s&logtype=%s&time=%s">%s</a><br>' % (bot, logtype, log[0], log[0])

print '</body></html>'

c.close()
