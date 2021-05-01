#!/usr/bin/env python3

import os, os.path
import re
import select
import shutil
import sqlite3
import subprocess
import sys
import threading
import time

import flask
from flask import request, jsonify


program_name = 'web-archiver'
dry_run = False

base_dir = os.path.join(os.environ['HOME'], '.cache', 'web-archive')
cookiefile = os.path.join(os.environ['HOME'], '.wget/cookies.txt')
queuefile = '%s/%s' % (base_dir, 'queue')
tcp_port = 4812

# forcefully work around python's stupid unicode handling
# python2
#reload(sys)
#sys.setdefaultencoding('utf-8')
# doesn't work:
#import codecs
#sys.stdout = codecs.getwriter('utf8')(sys.stdout)
## python3
import importlib
importlib.reload(sys)
#sys.setdefaultencoding('utf-8')
# TODO: test to make sure unicode page titles don't cause a crash

web = flask.Flask(program_name)
web.config["DEBUG"] = True
queue_lock = None
queue = []

quit = False


def main(args):
    """web-archiver.py
    A tool to monitor URLs opened, and archive a copy.
    Usage: web-archiver.py [OPTIONS]
      -d       --dry-run  Don't actually archive URLs, just print debug info
    """

    global mode
    global queue_lock
    global quit
    global dry_run

    i = 0
    while i < len(args):
        a = args[i]

        if a in ('-d', '--dry-run'):
            dry_run = True

        else:
            print(main.__doc__)
            return

        i += 1


    queue_lock = threading.Lock()

    try:
        archiver_thread = threading.Thread(target=archiver)
        archiver_thread.start()

        # if reloader is enabled, we end up with two archiver threads
        web.run(host='0.0.0.0', port=tcp_port, use_reloader=False)
        #web.run()
        # TODO: should probably run using a more stable server?
        # perhaps Gevent?
        # https://flask.palletsprojects.com/en/master/deploying/wsgi-standalone/#gevent

    except KeyboardInterrupt:
        quit = True

        archiver_thread.join()

        # TODO: also shut down the web server
        # ... which may be tricky
        # here's one idea for how:
        # https://stackoverflow.com/questions/15562446/how-to-stop-flask-application-without-using-ctrl-c
        # (the werkzeug answer from Ruben)


@web.route('/', methods=['GET'])
def frontpage():
    text = '''
    <html>
    <head>
    <title>Web Archiver</title>
    </head>
    <body>
    <h1>Web Archiver</h1>
    To submit URLs for archival, sent data via HTTP POST to
    /api/v1/submit in json format.
    <br /><br />
    For example:<br />
    <pre>
    [
      "http://example.com/1",
      ["http://example.com/2"],
      ["http://example.com/3", "Page Title 3"],
    ]
    </pre>

    A simple script to do this is:

    <pre>
    #!/bin/sh

    JSONFILE="$1" ; shift
    URL="$1" ; shift

    curl \\
      -X POST \\
      -H 'Content-type: application/json' \\
      -T "$JSONFILE" \\
      "$URL"
    </pre>
    </body>
    </html>
    '''
    return text


@web.route('/api/v1/submit', methods=['POST'])
def submit():

    global queue, queue_lock

    urls = request.json

    if not urls:
        return 'Error: No urls provided.\n'

    result = []

    # accept data in a few formats:
    # - "http://example.com"
    # - ["http://example.com"]
    # - ["http://example.com", "Page Title"]
    # ... and log everything else as errors
    for row in urls:
        if isinstance(row, str):
            url, title = row, ''
        elif isinstance(row, list):
            if len(row) == 1:
                url, title = row[0], ''
            elif len(row) == 2:
                url, title = row
            else:
                url, title = 'Error', 'expected 2 items in list, got %s' % (str(len(row)),)
        else:
            url, title = 'Error', 'expected str or list, got %s' % (str(type(row)),)

        task = (url, title)
        result.append(task)
        with queue_lock:
            queue.append(task)
            #log('queue: %s' % (task,))

    return jsonify(result)


def send_urls(urls, server):
    import requests
    res = requests.post(server, jsonify(urls))
    if res.ok:
        pass
    else:
        pass
    return res


def archiver():
    # don't run more than one instance
    if hasattr(archiver, 'running'):
        return
    archiver.running = True

    global queue, queue_lock

    while not quit:
        #fmt = '%Y-%m-%d %H:%M:%S'
        #now = time.strftime(fmt)
        #print('archiver(): %s' % (now,))
        #print('archiver(): %s' % (time.time(),))
        #time.sleep(1)

        grabbed = 0

        # Grab URLs from web UI
        urls = []
        with queue_lock:
            while queue:
                #log('dequeue: %s' % (queue[0],))
                urls.append(queue[0])
                del queue[0]

        # Grab URLs from the terminal
        # if the user typed something
        if select.select([sys.stdin,],[],[],0.0)[0]:
            line = sys.stdin.readline()
            line = line.strip()
            if line:
                urls.append((line, None))

        # Grab URLs from the queue file
        urls.extend(poll_queuefile())

        if urls:
            print('Queued URLs: %s' % (len(urls)))

        for url in urls:
            grab(*url)
            grabbed += 1

        if grabbed: log('Done. (%i urls)' % (grabbed))

        time.sleep(1)

    archiver.running = False


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
        if not dry_run:
            subprocess.check_output(cmd)
        else:
            log('grab(): %s' % (cmd,))
    except subprocess.CalledProcessError as e:
        log(e)


def blacklisted(url):
    # TODO: get this list from a config file or something
    patterns = [
            '^Error$',
            'www.facebook.com',
            'facebook.com/notifications',
            'facebook.com/messages',
            'connect.facebook.net',
            '^about:splash$',
            'discordapp.com/channels/',
            ]

    for p in patterns:
        found = re.search(p, url)
        if found:
            return True

    return False


def logged(f):
    def temp(*args, **kwargs):
        name = f.__name__
        log('%s()' % (name,))
        val = f(*args, **kwargs)
        log('%s() done' % (name,))
        return val
    return temp


def poll_queuefile():
    urls = []

    if not os.path.exists(queuefile):
        return urls

    fp = open(queuefile, 'r')
    lines = fp.readlines()
    fp.close()
    if lines:
        # replace it with an empty file
        open(queuefile, 'w').close()

    for line in lines:
        url = line.strip()
        if url:
            urls.append((url, None))

    return urls


def log(msg):
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    subsec = ('%.3f' % (time.time() % 1.0))[2:]
    print('%s.%s %s' % (now, subsec, msg))


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

