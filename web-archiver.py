#!/usr/bin/env python

import os, os.path
import select
import shutil
import sqlite3
import subprocess
import sys
import time

base_dir = os.path.join(os.environ['HOME'], '.cache', 'web-archive')

def main(args):
    prev_chrome_run = time.time() - 3600

    while True:
        grabbed = False

        # Grab URLs from Chromium
        print 'Chrome URLs:'
        urls = get_chrome_history_since(prev_chrome_run)
        prev_chrome_run = time.time()
        for url in urls:
            grab(url)
            grabbed = True

        # Grab URLs from the terminal
        for i in range(60):
            time.sleep(1)
            # the user typed something
            if select.select([sys.stdin,],[],[],0.0)[0]:
                line = sys.stdin.readline()
                grab(line.strip())
                grabbed = True
            else:
                if grabbed: print 'Done.'
                grabbed = False

def grab(url):
    print 'grab(%s)' % (url)

    if blacklisted(url):
        print 'skipping, blacklisted'
        return

    # make a directory for today
    newdir = os.path.join(base_dir, time.strftime('%Y-%m-%d'))
    if not os.path.exists(newdir):
        os.makedirs(newdir)
    os.chdir(newdir)

    # grab the page
    cmd = ('wget', '-p', '-k', '-o', '/dev/null', url)
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError, e:
        print e

def blacklisted(url):
    if 'www.facebook.com' in url: return True
    return False

def get_chrome_history_since(when):
    urls = []

    hist_file = os.path.join(os.environ['HOME'],'.config/chromium/Default/History')
    temp_hist_file = hist_file + '.temp'
    shutil.copyfile(hist_file, temp_hist_file)
    chrome_when = utc_to_chrome(when)

    db = sqlite3.connect(temp_hist_file)
    dbc = db.cursor()
    #help(dbc)

    dbc.execute('select * from urls where last_visit_time > %s' % (chrome_when))
    for row in dbc.fetchall():
        #print row
        title = row[2]
        print title
        urls.append(row[1])

    return urls

def utc_to_chrome(when):
    return int((when + 11644473600) * 1000000)

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

