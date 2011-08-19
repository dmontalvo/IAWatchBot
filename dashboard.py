#!/usr/bin/env python

from time import time, ctime
import os

running1 = "No"
if os.path.exists("/home/rkumar/iawb_lock.txt"):
    running1 = "Yes"
running2 = "No"
if os.path.exists("/home/rkumar/nytb_lock.txt"):
    running2 = "Yes"
running3 = "No"
if os.path.exists("/home/rkumar/pubbot_lock.txt"):
    running3 = "Yes"

zoneoffset = 25200
t = time()
next1 = ctime(t + 600 - t % 600 - zoneoffset)
next2 = ctime(t + 604800 - t % 604800 - zoneoffset)
next3 = ctime(t + 86400 - t % 86400 - zoneoffset)

print "Content-type: text/html\n\n"
print "<title>OL Bot Dashboard</title><b>OL Bot Dashboard</b><p>%s<p>" % ctime(time() - zoneoffset)
print '<table border=1><tr><th>Name</th><th>Owner</th><th>Running</th><th>Next Run</th><th>Error Messages</th><th>Logs</th></tr><tr><td>IAWatchBot</td><td>dmontalvo</td><td>%s</td><td>%s</td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?logtype=errors">errors</a></td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py">logs</a></td></tr><tr><td>nyt_bestsellers_bot</td><td>dmontalvo</td><td>%s</td><td>%s</td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?bot=nyt_bestsellers_bot&logtype=errors">errors</a></td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?bot=nyt_bestsellers_bot">logs</a></td></tr><tr><td>PublisherBot</td><td>dmontalvo</td><td>%s</td><td>%s</td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?bot=publisherbot&logtype=errors">errors</a></td><td><a href="http://ol-bots.us.archive.org/cgi-bin/logs.py?bot=publisherbot">logs</a></td></tr></table>' % (running1, next1, running2, next2, running3, next3)
