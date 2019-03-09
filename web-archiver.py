#!/usr/bin/env python

from __future__ import print_function
import os, os.path
import select
import shutil
import sqlite3
import subprocess
import sys
import time


base_dir = os.path.join(os.environ['HOME'], '.cache', 'web-archive')
cookiefile = os.path.join(os.environ['HOME'], '.wget/cookies.txt')
queuefile = '%s/%s' % (base_dir, 'queue')

# forcefully work around python's stupid unicode handling
reload(sys)
sys.setdefaultencoding('utf-8')
# doesn't work:
#import codecs
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)


def main(args):

    while True:
        grabbed = 0

        # Grab URLs from Chromium
        prev_chrome_run = time.time()
        urls = get_chrome_history_since_last()
        if urls:
            print('Chrome URLs:')
        for url in urls:
            grab(*url)
            grabbed += 1

        # Grab URLs from the terminal
        while (prev_chrome_run + 10) > time.time():
            time.sleep(0.2)
            # the user typed something
            if select.select([sys.stdin,],[],[],0.0)[0]:
                line = sys.stdin.readline()
                line = line.strip()
                if line:
                    grab(line, None)
                    grabbed += 1
                    log('...')
            #else:
            #    if grabbed: log('Done.')
            #    #grabbed = False

        grabbed += poll_queuefile()

        if grabbed: log('Done. (%i urls)' % (grabbed))


def grab(url, title):
    if not url: return
    log('grab(%s): %s' % (url, title))

    # make a directory for today
    # or maybe even per-hour, because people delete posts sometimes
    newdir = os.path.join(base_dir, time.strftime('%Y/%m/%d/%H'))
    if not os.path.exists(newdir):
        os.makedirs(newdir)
    os.chdir(newdir)

    # save it to the log
    with open('../urls.log', 'a') as fp:
        when = time.strftime('%Y-%m-%d %H:%M:%S')
        text = when + '\t' + url
        if title:
            text = text + '\t' + title
        fp.write(text + '\n')

    # maybe skip it?
    if blacklisted(url):
        print('skipping, blacklisted')
        return

    # keep track of the last few URLs, skip if this one was already
    # grabbed within the past ~5 minutes or the past ~2 URLs
    if not hasattr(grab, 'cache'):
        grab.cache = []
    now = time.time()
    # cache cleaning
    recent = []
    i = 0
    while i < len(grab.cache):
        c_url, c_time = grab.cache[i]
        if c_time < now - (3*60):  # expire after 3 minutes
            del grab.cache[i]
        else:
            recent.append(c_url)
            i += 1
    # skip URL if too recent in cache
    if url in recent:
        print('skipping, grabbed too recently')
        return

    # add new URL to cache
    grab.cache.append((url, now))

    # grab the page
    # TODO: include cookies from browser
    logfile = os.path.join(base_dir, 'wget.log')
    cmd = ('wget', '-p', '-k', '-H', '--timeout=15', '--tries=3', '--load-cookies', cookiefile, '-o', logfile, url)
    try:
        subprocess.check_output(cmd)
    except subprocess.CalledProcessError, e:
        log(e)


def blacklisted(url):
    patterns = [
            'www.facebook.com',
            'connect.facebook.net',
            'about:splash',
            ]
    for p in patterns:
        if p in url:
            return True
    #if 'www.facebook.com' in url:
    #    # facebook photo URLs no longer contain anything good...
    #    # ... and they're frigging huge now -- 2.4 MiB of random shit
    #    #if 'photo' in url:
    #    #    return False
    #    return True
    return False


def logged(f):
    def temp(*args, **kwargs):
        name = f.__name__
        log('%s()' % (name,))
        val = f(*args, **kwargs)
        log('%s() done' % (name,))
        return val
    return temp


#@logged
def get_chrome_history_since_last():
    urls = []

    hist_file = os.path.join(os.environ['HOME'],'.config/chromium/Default/History')
    temp_hist_file = hist_file + '.temp'
    shutil.copyfile(hist_file, temp_hist_file)

    db = sqlite3.connect(temp_hist_file)
    dbc = db.cursor()
    #help(dbc)

    # grab history since last successful value, if possible...
    if hasattr(get_chrome_history_since_last, 'last_timestamp'):
        chrome_when = get_chrome_history_since_last.last_timestamp + 1
    else:
        # otherwise, get the most recent value for comparison
        query = 'select * from urls order by last_visit_time desc limit 1'
        dbc.execute(query)
        row = dbc.fetchone()
        print('Last URL loaded: %s' % (row,))
        timestamp = row[5]
        get_chrome_history_since_last.last_timestamp = timestamp
        chrome_when = timestamp + 1

    query = 'select * from urls where last_visit_time >= %s' % (chrome_when)
    #log(query)
    dbc.execute(query)
    for row in dbc.fetchall():
        #print(row)
        url = row[1]
        title = row[2]
        timestamp = row[5]
        get_chrome_history_since_last.last_timestamp = timestamp
        #print(title)
        urls.append((url, title))

    return urls


def poll_queuefile():
    grabbed = 0
    if os.path.exists(queuefile):
        fp = open(queuefile, 'r')
        lines = fp.readlines()
        fp.close()
        if lines:
            # remove or empty the file
            #os.unlink(queuefile)
            open(queuefile, 'w').close()

            for line in lines:
                grab(line.strip(), None)
                grabbed += 1

    return grabbed


def log(msg):
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    subsec = ('%.3f' % (time.time() % 1.0))[2:]
    print('%s.%s %s' % (now, subsec, msg))


def utc_to_chrome(when):
    # Chrome timestamps are formatted as the number of microseconds since 
    # 1601-01-01
    # sqlite3 'select strftime('%s', '1601-01-01');'
    seconds_from_1600_to_1970 = 11644473600
    ans = int((when + seconds_from_1600_to_1970) * 1000000)
    print('utc_to_chrome(%s) => %s' % (when, ans))
    return ans


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

