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
import re
import sqlite3

subjlist = ['in library', 'lending library', 'accessible book', 'overdrive', 'protected daisy']

def send_email(fromaddr, toaddrs, subj, message):
    msg = ("Subject: %s\r\nFrom: %s\r\nTo: %s\r\n\r\n" % (subj, fromaddr, ", ".join(toaddrs)))
    msg += message
    server = smtplib.SMTP('mail.archive.org')
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

def bad_links(before, after):
    bef = str(before)
    aft = str(after)
    badlinks = len(re.findall("http://", aft)) - len(re.findall("loc.gov", aft)) - len(re.findall("wikipedia.org", aft)) - len(re.findall("archive.org", aft)) - len(re.findall("openlibrary.org", aft))
    prevbadlinks = len(re.findall("http://", bef)) - len(re.findall("loc.gov", bef)) - len(re.findall("wikipedia.org", bef)) - len(re.findall("archive.org", bef)) - len(re.findall("openlibrary.org", bef))
    return badlinks - prevbadlinks > 2

def insert(linenum, key, author, problem, comment):
    stuff = (linenum, key, author, problem, comment, 0)
    curs.execute("""insert into vandalism values (?, ?, ?, ?, ?, ?)""", stuff)
    conn.commit()

# Make sure only one instance of the bot is running at one time
if os.path.exists("iawb_lock.txt"):
    print "Bot already running. Exiting."
    exit()
i = open("iawb_lock.txt", 'w')

t = asctime()
s = time()

try:
    # Connect to sqlite database
    global conn
    global curs
    conn = sqlite3.connect('/home/dmontalvo/IAWatchBot/reports.sqlite')
    curs = conn.cursor()
    curs.execute("""select * from vandalism""")
    linenum = len(curs.fetchall()) + 1

    # Find the last checked edit
    if os.path.exists("lastedit.txt"):
        j = open("lastedit.txt", 'r')
        last_id = j.read()
        j.close()
    else:
        last_id = 0

    # Write to the log
    g = open("/var/www/logs/IAWatchBot/%s" % t, 'w')
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
        auth = "[None]"
        if y['author'] is not None:
            author = "http://openlibrary.org%s" % y['author']['key']
            auth =  y['author']['key']
        elif y['ip'] is not None:
            author = "openlibrary.org/admin/ip/%s" % y['ip']
            auth = y['ip']
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
                            #send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "IA id modified", "The IA id has been modified by %s for the edition http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))   
                            insert(linenum, z['key'], auth, "IA id modified", y['comment'])
                            linenum += 1
                    else:
                        g.write("Status: ocaid deleted from %s\n" % z['key'])
                        problem = True
                        #send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "IA id deleted", "The IA id has been deleted by %s for the edition http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))
                        insert(linenum, z['key'], auth, "IA id deleted", y['comment'])
                        linenum += 1
                if not problem and bad_links(d, c):
                    problem = True
                    g.write("Status: spam added to %s\n" % z['key'])
                    #send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "Possible spam detected", "Suspicious links have been added by %s for the edition http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))
                    insert(linenum, z['key'], auth, "untrusted links", y['comment'])
                    linenum += 1
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
                removedlist = []
                for subj in subjlist:
                    if d.has_key('subjects') and subj in dsubjs:
                        if not (c.has_key('subjects') and subj in csubjs):
                            g.write("Status: %s subject deleted from %s\n" % (subj, z['key']))
                            problem = True
                            removedlist.append(subj)
                if len(removedlist) > 0:
                    #send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "Protected subject(s) deleted", "Protected subjects %s have been deleted by %s for the work http://openlibrary.org%s with the following comment: '%s'" % (removedlist, author, z['key'], y['comment']))
                    insert(linenum, z['key'], auth, "subjects deleted", y['comment'])
                    linenum += 1
                if not problem and bad_links(d, c):
                    problem = True
                    g.write("Status: spam added to %s\n" % z['key'])
                    #send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "Possible spam detected", "Suspicious links have been added by %s for the work http://openlibrary.org%s with the following comment: '%s'" % (author, z['key'], y['comment']))
                    insert(linenum, z['key'], auth, "untrusted links", y['comment'])
                    linenum += 1
            if not problem:
                g.write("Status: %s fine\n" % z['key'])

    # Close sqlite connection
    curs.close()

    # Update the last checked edit
    j = open("lastedit.txt", 'w')
    j.write(x[0]['id'])
    j.close()

    # Finish writing to log
    g.write("Ended at: %s\n" % asctime())
    g.write("Total run time: %s seconds\n" % (time() - s))
    g.close()
    os.remove("iawb_lock.txt")

except:
    error = traceback.format_exc()
    print error
    el = open("/var/www/errors/iawb_errors.txt","a")
    el.write("%s\n%s\n\n" % (t, error))
    os.remove("iawb_lock.txt")
