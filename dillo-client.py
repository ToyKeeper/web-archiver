#!/usr/bin/env python3


import os
import re
import subprocess
import time

from client import Client

quit = False


def main(args):
    """Watch my X11 session log for new URLs opened in Dillo, and log those
    URLs to my web-archiver task queue so they'll be automatically saved.
    """

    cl = Client()
    set_defaults(cl.cfg)
    cl.start()

    try:
        logtail(cl)
    except KeyboardInterrupt:
        quit = True

    cl.stop()


def set_defaults(cfg):
    home = os.environ['HOME']
    inpath = '%s/.xsession-errors' % home

    cfg.doc(dillo_logtail_path='Which file to watch for new URLs')
    cfg.default(dillo_logtail_path=inpath)


def logtail(client):
    inpath = client.cfg.dillo_logtail_path

    urlpat = re.compile(r'''^Nav_open_url:.*url='([^']+)'$''')

    for line in tail(['tail', '-n', '1', '-F', inpath]):
        found = urlpat.search(line)
        if found:
            url = found.group(1)
            print('archive: %s' % url)
            client.grab(url)

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

