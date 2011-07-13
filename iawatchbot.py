#!/usr/bin/python                                                             

# IAWatchBot                                                                 
# by Daniel Montalvo    

from time import asctime, time, ctime
import time
import calendar
import urllib
import json
import os.path
import smtplib
import string
import traceback
import sys
import re
import psycopg2
import language

ld = language.LangDetect()

subjlist = ['in library', 'lending library', 'accessible book', 'overdrive', 'protected daisy']

def send_email(fromaddr, toaddrs, subj, message):
    msg = ("Subject: %s\r\nFrom: %s\r\nTo: %s\r\n\r\n" % (subj, fromaddr, ", ".join(toaddrs)))
    msg += message
    server = smtplib.SMTP('mail.archive.org')
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()

def bad_links(before, after):
    aft = str(after)    
    badlinks = len(re.findall("http://", aft)) - len(re.findall("loc.gov", aft)) - len(re.findall("wikipedia.org", aft)) - len(re.findall("archive.org", aft)) - len(re.findall("openlibrary.org", aft))
    prevbadlinks = 0
    if before is not None:
        bef = str(before)
        prevbadlinks = len(re.findall("http://", bef)) - len(re.findall("loc.gov", bef)) - len(re.findall("wikipedia.org", bef)) - len(re.findall("archive.org", bef)) - len(re.findall("openlibrary.org", bef))
    return badlinks - prevbadlinks > 2

def insert(time, key, title, author, comment, revision, problem):
    curs.execute("insert into reports (time, key, title, author, comment, revision, problem, resolved) values (%s, %s, %s, %s, %s, %s, %s, %s)", (time, key, title, author, comment, revision, problem, 0))
    conn.commit()

# Make sure only one instance of the bot is running at one time
if os.path.exists("iawb_lock.txt"):
    print "Bot already running. Exiting."
    exit()
i = open("iawb_lock.txt", 'w')

# Get start time
t = asctime()
s = time.time()

try:
    # Connect to database
    global conn
    global curs
    conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
    curs = conn.cursor()
    curs.execute("""select * from reports where resolved=0""")
    unresolved = curs.fetchall()
    keylist = []
    for report in unresolved:
        keylist.append(report[1])

    # Find the last checked edit
    if os.path.exists("lastedit.txt"):
        j = open("lastedit.txt", 'r')
        last_id = j.read()
        j.close()
    else:
        last_id = 0

    # Start creating the log
    logstring = 'Started at: %s\n' % t

    # Get the whitelist
    adminquery = urllib.urlopen("http://openlibrary.org/usergroup/admin.json")
    l = json.JSONDecoder().decode(adminquery.read())
    whitelist = []
    adminlist = []
    for member in l['members']:
        whitelist.append(member['key'])
        adminlist.append(member['key'])
    apiquery = urllib.urlopen("http://openlibrary.org/usergroup/api.json")
    n = json.JSONDecoder().decode(apiquery.read())
    for member in n['members']:
        whitelist.append(member['key'])

    # Query for recent changes
    changesquery = urllib.urlopen("http://openlibrary.org/recentchanges.json?limit=1000")
    x = json.JSONDecoder().decode(changesquery.read())

    # Iterate over the recent changes
    for y in x:
        if y['id'] <= last_id:
            break
        logstring += "Checking id: %s\n" % y['id']
        author = "[None]"
        auth = "[None]"
        if y['author'] is not None:
            author = "http://openlibrary.org%s" % y['author']['key']
            auth =  y['author']['key']
        elif y['ip'] is not None:
            author = "openlibrary.org/admin/ip/%s" % y['ip']
            auth = y['ip']
        if y['author'] is not None and auth in whitelist:
            logstring += "Status: fine\n"

            # Automatically resolve if admin edited
            if auth in adminlist:
                for z in y['changes']:
                    if z['key'] in keylist:
                        curs.execute("""update reports set resolved=1 where key=%s""", (z['key'],))
                        conn.commit()
            continue

        # Iterate over each item in each change
        for z in y['changes']:
            problem = False
            rev = z['revision']
            key = z['key']
            title = key
            try:
                currenturl = urllib.urlopen("http://openlibrary.org" + key + ".json?v=" + str(rev))
                currentitem = json.JSONDecoder().decode(currenturl.read())
            except ValueError:
                continue
            previousitem = None
            if rev > 1:
                previousurl = urllib.urlopen("http://openlibrary.org" + key + ".json?v=" + str(rev-1))
                previousitem = json.JSONDecoder().decode(previousurl.read())
            if currentitem.has_key('title'):
                title = currentitem['title']

            # If it's an edition, check for IA ids
            if "/books/" in key and rev > 1:
                if currentitem.has_key('title'):
                    title = currentitem['title']            

                # if it had an IA id, make sure it wasn't changed/removed
                if previousitem.has_key("ocaid") and previousitem['ocaid'] != "":
                    if currentitem.has_key("ocaid"):
                        if currentitem["ocaid"] != previousitem["ocaid"]:
                            logstring += "Status: ocaid modified for %s\n" % key
                            problem = True
                            insert(y['timestamp'], key, title, auth, y['comment'], rev, "IA id modified")
                    else:
                        logstring += "Status: ocaid deleted from %s\n" % key
                        problem = True
                        insert(y['timestamp'], key, title, auth, y['comment'], rev, "IA id deleted")

            # Check works for deleted subjects
            elif "/works/" in key and rev > 1:
                if currentitem.has_key('title'):
                    title = currentitem['title']
                csubjs = []
                if currentitem.has_key('subjects'):
                    for subj in currentitem['subjects']:
                        csubjs.append(string.lower(subj))
                dsubjs = []
                if previousitem.has_key('subjects'):
                    for subj in previousitem['subjects']:
                        dsubjs.append(string.lower(subj))
                removedlist = []
                for subj in subjlist:
                    if previousitem.has_key('subjects') and subj in dsubjs:
                        if not (currentitem.has_key('subjects') and subj in csubjs):
                            logstring += "Status: %s subject deleted from %s\n" % (subj, key)
                            problem = True
                            removedlist.append(subj)
                if len(removedlist) > 0:
                    insert(y['timestamp'], key, title, auth, y['comment'], rev, "subjects deleted")

            # Check for removed fields
            if ("/works/" in key or "/books/" in key) and rev > 1 and not problem:
               removedfields = []
               for field in previousitem:
                   if field == 'id':
                       continue
                   if previousitem[field] != "" and previousitem[field] != [] and previousitem[field] != {} and not currentitem.has_key(field):
                       removedfields.append(field)
                       if not problem:
                           try:
                               t1 = time.strptime(previousitem['last_modified']['value'], '%Y-%m-%dT%H:%M:%S.%f')
                           except ValueError:
                               t1 = time.strptime(previousitem['last_modified']['value'], '%Y-%m-%d %H:%M:%S.%f')
                           try:
                               t2 = time.strptime(currentitem['last_modified']['value'], '%Y-%m-%dT%H:%M:%S.%f')
                           except ValueError:
                               t2 = time.strptime(currentitem['last_modified']['value'], '%Y-%m-%d %H:%M:%S.%f')
                           t3 = calendar.timegm(t1)
                           t4 = calendar.timegm(t2)
                           lastedit = t3 - t4
                           if lastedit > 600 or lastedit < -600:
                               problem = True
               if problem:
                   logstring += "Status: fields %s removed from %s\n" % (removedfields, key)
                   insert(y['timestamp'], key, title, auth, y['comment'], rev, "fields removed")

            # Check for suspicious links
            if (not problem) and ('/works/' in key or '/books/' in key) and bad_links(previousitem, currentitem):
                    problem = True
                    logstring += "Status: spam added to %s\n" % key
                    insert(y['timestamp'], key, title, auth, y['comment'], rev, "untrusted links")

            # Check for language change in title or description
            if (not problem) and ('/works/' in key or '/books/' in key) and rev > 1:
                if currentitem.has_key('title') and previousitem.has_key('title'):
                    curlang = ld.detect(currentitem['title'])
                    if curlang != "en":
                        prevlang = ld.detect(previousitem['title'])
                        if curlang != prevlang:
                            problem = True
                            logstring += "Status: language change in title of %s\n" % key
                            insert(y['timestamp'], key, title, auth, y['comment'], rev, "language change in title")
                if not problem and previousitem.has_key('description') and currentitem.has_key('description'):
                    if type(currentitem['description']) == dict and currentitem['description'].has_key('value'):
                        curlang = ld.detect(currentitem['description']['value'])
                    else:
                        curlang = ld.detect(currentitem['description'])
                    if curlang != "en" and previousitem.has_key('description'):
                        if type(previousitem['description']) == dict and previousitem['description'].has_key('value'):
                            prevlang = ld.detect(previousitem['description']['value'])
                        else:
                            prevlang = ld.detect(previousitem['description'])
                        if curlang != prevlang:
                            problem = True
                            logstring += "Status: language change in description of %s\n" % key
                            insert(y['timestamp'], key, title, auth, y['comment'], rev, "language change in description")

            if not problem:
                logstring += "Status: %s fine\n" % key

    # Check for unresolved reports once per day
    curs.execute("""select * from reports where resolved=0""")
    num_unresolved = len(curs.fetchall())
    if num_unresolved > 0 and (s % 86400 < 60 or s % 86400 > 86340):
        verb = "are"
        noun = "reports"
        pronoun = "them"
        if num_unresolved == 1:
            verb = "is"
            noun = "report"
            pronoun = "it"
        send_email("daniel.m@archive.org", ["openlibrary@archive.org"], "Unresolved Vandalism Reports", "There %s %s unresolved vandalism %s. To resolve %s, visit the Vandalism Center: http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py" % (verb, num_unresolved,  noun, pronoun))          

    # Update the last checked edit
    j = open("lastedit.txt", 'w')
    j.write(x[0]['id'])
    j.close()

    # Finish writing to log
    logstring += "Ended at: %s\n" % asctime()
    logstring += "Total run time: %s seconds\n" % (time.time() - s)
    curs.execute("insert into logs (time, bot, logtype, data) values (%s, 'iawatchbot', 'logs', %s)", (t, logstring))
    conn.commit()
    os.remove("iawb_lock.txt")
    curs.close()

except:
    error = traceback.format_exc()
    print error
    curs.execute("insert into logs (time, bot, logtype, data) values (%s, 'iawatchbot', 'errors', %s)", (t, error))
    conn.commit()
    curs.close
    os.remove("iawb_lock.txt")
