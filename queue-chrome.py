#!/usr/bin/env python3


import os, os.path
import sqlite3
import subprocess
import sys
import time

from client import Client

# forcefully work around python's stupid unicode handling
# python2
#reload(sys)
#sys.setdefaultencoding('utf-8')
# doesn't work:
#import codecs
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)
# python3
import importlib
importlib.reload(sys)
#sys.setdefaultencoding('utf-8')


quit = False


def main(args):
    """Watch my Chrome logs for new URLs, and log those
    to my web-archiver task queue so they'll be automatically saved.
    """

    cl = Client()

    try:
        chrome_monitor(cl)
    except KeyboardInterrupt:
        quit = True

    cl.stop()


def chrome_monitor(client):
    while not quit:

        # Grab URLs from Chromium
        prev_chrome_run = time.time()
        urls = []
        try:
            urls = get_chrome_history_since_last()
        except sqlite3.OperationalError:
            print('Chrome History... failed')
        if urls:
            print('Chrome URLs: %s' % (len(urls),))

            for url, title in urls:
                client.grab(url, title)

        while (prev_chrome_run + 10) > time.time():
            time.sleep(0.2)

            if quit:
                return


def log(msg):
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    subsec = ('%.3f' % (time.time() % 1.0))[2:]
    print('%s.%s %s' % (now, subsec, msg))


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
    #temp_hist_file = os.path.join(os.environ['HOME'],'.config/chromium/foo/Foo')
    # Stupid, nasty kludge: Chrome keeps its databases locked at all times,
    # and SQLite absolutely refuses to open the file even as read-only,
    # and symlinks/hardlinks/bind-mounts don't help, so the only workable
    # solution is to copy the file before reading from it...  which sucks.
    # Especially when Chrome's history file is hundreds of megabytes.
    temp_hist_file = hist_file + '.temp'

    # if file hasn't been updated, abort
    try:
        real, temp = os.stat(hist_file), os.stat(temp_hist_file)
        if real.st_mtime <= temp.st_mtime:
            #print('Chrome History... not updated, skipping')
            return urls
    except OSError:  # if file doesn't exist, maybe we haven't made it yet
        pass

    print('Chrome History... opening')

    #shutil.copyfile(hist_file, temp_hist_file)
    run('rsync', '-a', hist_file, temp_hist_file)

    db = sqlite3.connect(temp_hist_file)
    #db = sqlite3.connect('file:%s?mode=ro' % temp_hist_file, uri=True)  # python3 only
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

    print('Chrome History... done (%s new items)' % (len(urls)))
    return urls


def utc_to_chrome(when):
    # Chrome timestamps are formatted as the number of microseconds since 
    # 1601-01-01
    # sqlite3 'select strftime('%s', '1601-01-01');'
    seconds_from_1600_to_1970 = 11644473600
    ans = int((when + seconds_from_1600_to_1970) * 1000000)
    print('utc_to_chrome(%s) => %s' % (when, ans))
    return ans


def run(*cmd):
    """Execute a command (tuple), return its errcode and text output"""
    err = 0
    text = ''
    print('run: %s' % (cmd,))

    # catches stdout+stderr+retcode
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, close_fds=True)
    # wait for process to finish and get its output
    stdout, foo = p.communicate()
    text = stdout.decode()
    err = p.returncode

    return err, text


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

