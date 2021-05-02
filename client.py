#!/usr/bin/env python

import requests
import threading
import time

import pycfg

program_name = 'web-archiver'


def main(args):
    pass


class Client:

    def __init__(self):
        self.queue = []
        self.queue_lock = threading.Lock()
        self.done = False
        self.urls = []

        self.cfg = pycfg.config(program_name)
        self.set_defaults()

    def set_defaults(self):
        cfg = self.cfg

        cfg.doc(server_url='Front page of the archive server')
        cfg.default(server_url='http://localhost:4812/')

        cfg.doc(retry_time='How long to wait between tries when requests fail')
        cfg.default(retry_time=30)

    def start(self):
        self.cfg.load()
        #self.cfg.validate()

        self.thread = threading.Thread(target=self.loop)
        self.thread.start()

    def stop(self):
        self.done = True
        self.thread.join()

    def grab(self, url, title=None):
        """Add a URL to the queue for later processing.
        """
        if title:
            req = (url, title)
        else:
            req = url
        with self.queue_lock:
            self.queue.append(req)

    def loop(self):
        """Accept URLs from the queue, and send them to the server.
        Keep trying until each batch succeeds.
        """

        server_url =  self.cfg.server_url
        if not server_url.endswith('/'):
            server_url = server_url + '/'
        server_url = server_url + 'api/v1/submit'

        while not self.done:

            # move newly-detected urls into our private list
            with self.queue_lock:
                while self.queue:
                    self.urls.append(self.queue[0])
                    del self.queue[0]

            # send urls to the archive server
            if self.urls:
                try:
                    post(self.urls, server_url)
                    self.urls = []
                except ConnectionError:
                    print('Error: failed to post %s urls, will try again' \
                          ' in %ss' % (len(self.urls), self.cfg.retry_time))
                    time.sleep(self.cfg.retry_time)

            time.sleep(1)


def post(urls, server_url):
    """POST urls in json format to a web server.
    """
    try:
        res = requests.post(server_url, json=urls)
        if res.ok:
            #print(res.json())
            pass
        else:
            raise ConnectionError('post() response not ok')
    except requests.exceptions.RequestException:
        # TODO: handle failed request
        raise ConnectionError('post() attempt failed')


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])

