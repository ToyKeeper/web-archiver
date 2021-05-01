#!/usr/bin/env python3

import flask
from flask import request, jsonify
import threading
import time

program_name = 'web-archiver'

web = flask.Flask(program_name)
web.config["DEBUG"] = True


def main(args):
    archiver_thread = threading.Thread(target=archiver)
    archiver_thread.start()

    # if reloader is enabled, we end up with two archiver threads
    web.run(use_reloader=False)
    #web.run()

    archiver_thread.join()
    """
    # run a web server in the background to accept URLs
    # FIXME: doesn't work if flask debug mode is enabled
    # "ValueError: signal only works in main thread of the main interpreter"
    web_thread = threading.Thread(target=web.run)
    web_thread.start()

    archiver()

    web_thread.join()
    """


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
      "url1",
      ["url2"],
      ["url3", "Title 3"],
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

        result.append((url, title))

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

    while True:
        fmt = '%Y-%m-%d %H:%M:%S'
        now = time.strftime(fmt)
        #print('archiver(): %s' % (now,))
        print('archiver(): %s' % (time.time(),))
        time.sleep(1)

    archiver.running = False


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

