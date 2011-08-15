#!/usr/bin/env python

import sqlite3
import cgi
import psycopg2

REPORTS_PER_PAGE = 50

conn = psycopg2.connect('dbname=vandalism user=dmontalvo password=iawatchbot')
c = conn.cursor()

form = cgi.FieldStorage()
pagenum = 1
display = "unresolved"
if form.getlist("page"):
    pagenum = int(form.getlist("page")[0])
if form.getlist("display"):
    display = form.getlist("display")[0]
if form.getlist("checkbox"):
    for item in form.getlist("checkbox"):
        c.execute("""update reports set resolved=1 where key=%s""", (item,))
        conn.commit()

if display == "all":
    c.execute('select * from reports')
elif display == "resolved":
    c.execute('select * from reports where resolved=1')
else:
    c.execute('select * from reports where resolved=0')
reports = c.fetchall()
reports.sort()
reports.reverse()
maxindex = REPORTS_PER_PAGE * pagenum
minindex = maxindex - REPORTS_PER_PAGE
displaylist = reports[minindex:maxindex]
any_unresolved = False
for report in displaylist:
    if report[7] == 0:
        any_unresolved = True
status = " disabled"
if any_unresolved:
    status = ""

print "Content-type: text/html; charset=UTF-8\n\n"
print "<html><body><title>Vandalism Center</title><b>Vandalism Reports</b><p>If you edit one of the reported items, the report will be automatically resolved within 10 minutes. If a report requires no edit, please submit the report to resolve it. <p>"
print """<form name="myform" method="POST"><table border=1><tr><th>Time of Edit</th><th>Item</th><th>Author</th><th>Comment</th><th>Problem</th><th><div class="radio"><input type="checkbox" name="checkall" id="checkall"%s> <label for="checkall">I've dealt with this</label></div></th></tr>""" % status
for line in displaylist:
    tag = '<tr>'
    status = ""
    if line[7] == 1:
        tag = '<tr bgcolor="#CCCCCC">'
        status = " disabled"
    if "/people/" in line[3]:
        author = '<a href="http://openlibrary.org%s">%s</a>' % (line[3], line[3][8:])
    else:
        author = '<a href="http://openlibrary.org/admin/ip/%s">%s</a>' % (line[3], line[3])
    dt = "%s/%s/%s %s:%s" % (line[0][5:7], line[0][8:10], line[0][0:4], line[0][11:13], line[0][14:16])
    diff = ""
    if line[5] != 1:
        diff = ' - <a href="http://openlibrary.org%s?b=%s&a=%s&_compare=Compare&m=diff"><font size=1>diff</font></a>' % (line[1], line[5], line[5]-1)
    tablerow =  '%s<td>%s</td><td><a href="http://openlibrary.org%s">%s</a>%s</td><td>%s</td><td>%s</td><td>%s</td><td><input type="checkbox" name="checkbox" value="%s"%s></td></tr>' % (tag, dt, line[1], line[2], diff, author, line[4], line[6], line[1], status)
    print tablerow
print '</table><br>'
print '<div align="center"><input type="submit" value="Submit"></div></form>'
print "Page: "
for x in range(1, (len(reports)+REPORTS_PER_PAGE-1)/REPORTS_PER_PAGE+1):
    if x == pagenum:
        print x
    else:
        print '<a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py?page=%s&display=%s">%s</a>' % (x, display , x)
if display == "resolved":
    print '<br>Display: <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py">Unresolved</a> Resolved <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py?display=all">All</a>'
elif display == "all":
    print '<br>Display: <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py">Unresolved</a> <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py?display=resolved">Resolved</a> All'
else:
    print '<br>Display: Unresolved <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py?display=resolved">Resolved</a> <a href="http://ol-bots.us.archive.org/cgi-bin/vandalismcenter.py?display=all">All</a>'

print '<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.3.2/jquery.min.js"></script>'
print """<script type="text/javascript">
$(function () {
$('#checkall').click(function () {
$(this).parents('').find(':checkbox').attr('checked', this.checked);
});
});
</script>"""
print '</body></html>'

c.close()
