#!/usr/bin/env python

import requests
import threading
import time

#default_server = 'http://b.xyzz.org:4812/api/v1/submit'
default_server = 'http://localhost:4812/api/v1/submit'


def main(args):
    pass


class Client:

    def __init__(self):
        self.queue = []
        self.queue_lock = threading.Lock()
        self.done = False
        self.urls = []
        self.retry_time = 30

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

        while not self.done:

            # move newly-detected urls into our private list
            with self.queue_lock:
                while self.queue:
                    self.urls.append(self.queue[0])
                    del self.queue[0]

            # send urls to the archive server
            if self.urls:
                try:
                    post(self.urls)
                    self.urls = []
                except ConnectionError:
                    print('Error: failed to post %s urls, will try again' \
                          ' in %ss' % (len(self.urls), self.retry_time))
                    time.sleep(self.retry_time)

            time.sleep(1)


def post(urls, server=None):
    """POST urls in json format to a web server.
    """
    if not server:
        # TODO: get URI from user config
        server = default_server
    try:
        res = requests.post(server, json=urls)
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

