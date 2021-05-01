#!/usr/bin/env python3


import os
import re
import subprocess
import threading
import time

from send import post

queue = []
queue_lock = None
quit = False


def main(args):
    """Watch my X11 session log for new URLs opened in Dillo, and log those
    URLs to my web-archiver task queue so they'll be automatically saved.
    """

    global queue_lock

    queue_lock = threading.Lock()

    web_thread = threading.Thread(target=submit_urls)
    web_thread.start()

    try:
        logtail()
    except KeyboardInterrupt:
        quit = True

    web_thread.join()


def submit_urls():
    global queue, queue_lock

    urls = []

    while not quit:

        # move newly-detected urls into our private list
        with queue_lock:
            while queue:
                urls.append(queue[0])
                del queue[0]

        # send urls to the archive server
        if urls:
            try:
                post(urls)
                urls = []
            except ConnectionError:
                print('Error: failed to post %s urls, will try again' \
                      % (len(urls),))
                time.sleep(30)

        time.sleep(1)


def logtail():
    global queue, queue_lock

    home = os.environ['HOME']
    inpath = '%s/.xsession-errors' % home

    urlpat = re.compile(r'''^Nav_open_url:.*url='([^']+)'$''')

    for line in tail(['tail', '-n', '1', '-F', inpath]):
        found = urlpat.search(line)
        if found:
            url = found.group(1)
            print('archive: %s' % url)
            with queue_lock:
                queue.append(url)

        if quit:
            return


def tail(cmd):
    """Stream one line at a time from a long-running command.
    (is easier than re-implementing "tail -F" in python)
    """
    fp = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(fp.stdout.readline, ''):
        yield stdout_line
    fp.stdout.close()
    return_code = fp.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

