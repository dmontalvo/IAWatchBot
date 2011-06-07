#!/usr/bin/python                                                             

# IAWatchBot                                                                 
# by Daniel Montalvo    

from time import strftime, asctime, altzone, time
import urllib
import json
import os.path
import smtplib
import string
import traceback
import sys

subjlist = ['in library', 'lending library', 'accessible book', 'overdrive', 'protected daisy']

def send_email(fromaddr, toaddrs, subj, message):
    msg = ("Subject: %s\r\nFrom: %s\r\nTo: %s\r\n\r\n" % (subj, fromaddr, ", ".join(toaddrs)))
    msg += message
    server = smtplib.SMTP('mail.archive.org')
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

# Make sure only one instance of the bot is running at one time
if os.path.exists("lock.txt"):
    print "Bot already running. Exiting."
    exit()
i = open("lock.txt", 'w')

t = asctime()
s = time()

try:
    # Find the last checked edit
    if os.path.exists("lastedit.txt"):
        j = open("lastedit.txt", 'r')
        last_id = j.read()
        j.close()
    else:
        last_id = 0

    # Write to the log
    g = open("logs/%s" % t, 'w')
    g.write('Started at: %s\n' % t)

    # Get the whitelist
    k = urllib.urlopen("http://openlibrary.org/usergroup/admin.json")
    l = json.JSONDecoder().decode(k.read())
    whitelist = []
    for member in l['members']:
        whitelist.append(member['key'])
    m = urllib.urlopen("http://openlibrary.org/usergroup/api.json")
    n = json.JSONDecoder().decode(m.read())
    for member in n['members']:
        whitelist.append(member['key'])

    # Query for recent changes
    f = urllib.urlopen("http://openlibrary.org/recentchanges.json?limit=1000")
    x = json.JSONDecoder().decode(f.read())

    # Iterate over the recent changes
    for y in x:
        if y['id'] <= last_id:
            break
        g.write("Checking id: %s\n" % y['id'])
        author = "[None]"
        if y['author'] is not None:
            author = "http://openlibrary.org%s" % y['author']['key']
        elif y['ip'] is not None:
            author = y['ip']
        if y['author'] is not None and y['author']['key'] in whitelist:
            g.write("Status: fine\n")
            continue
        for z in y['changes']:
            problem = False
            rev = z['revision']

            # If it's an edition, check for IA ids
            if z['key'][:9] == "/books/OL":
                url = "http://openlibrary.org" + z['key'] + ".json?v=" + str(rev)
                a = urllib.urlopen(url)
                url = "http://openlibrary.org" + z['key'] + ".json?v=" + str(rev-1)
                b = urllib.urlopen(url)
                c = json.JSONDecoder().decode(a.read())
                d = json.JSONDecoder().decode(b.read())
            
                # if it had an IA id, make sure it wasn't changed/removed
                if d.has_key("ocaid") and d['ocaid'] != "":
                    if c.has_key("ocaid"):
                        if c["ocaid"] != d["ocaid"]:
                            g.write("Status: ocaid modified for %s\n" % z['key'])
                            problem = True
                            send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "IA id modified", "The IA id has been modified by %s for the edition http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))                        
                    else:
                        g.write("Status: ocaid deleted from %s\n" % z['key'])
                        problem = True
                        send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "IA id deleted", "The IA id has been deleted by %s for the edition http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))
            elif z['key'][:9] == "/works/OL":
                url = "http://openlibrary.org" + z['key'] + ".json?v=" + str(rev)
                a = urllib.urlopen(url)
                url = "http://openlibrary.org" + z['key'] + ".json?v=" + str(rev-1)
                b = urllib.urlopen(url)
                c = json.JSONDecoder().decode(a.read())
                d = json.JSONDecoder().decode(b.read())
                csubjs = []
                if c.has_key('subjects'):
                    for subj in c['subjects']:
                        csubjs.append(string.lower(subj))
                dsubjs = []
                if d.has_key('subjects'):
                    for subj in d['subjects']:
                        dsubjs.append(string.lower(subj))
                for subj in subjlist:
                    if d.has_key('subjects') and subj in dsubjs:
                        if not (c.has_key('subjects') and subj in csubjs):
                            g.write("Status: %s subject deleted from %s\n" % (subj, z['key']))
                            problem = True
                            send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "%s subject deleted" % subj, "The '%s' subject has been deleted by %s for the work http://openlibrary.org%s with the following comment: '%s'" % (subj, author, z['key'], y['comment']))
            if not problem:
                g.write("Status: %s fine\n" % z['key'])

    # Update the last checked edit
    j = open("lastedit.txt", 'w')
    j.write(x[0]['id'])
    j.close()

    # Finish writing to log
    g.write("Ended at: %s\n" % asctime())
    g.write("Total run time: %s seconds\n" % (time() - s))
    g.close()
    os.remove("lock.txt")

except:
    error = traceback.format_exc()
    print error
    el = open("/var/www/errors/errorlog.txt","a")
    el.write("%s\n%s\n\n" % (t, error))
    os.remove("lock.txt")
