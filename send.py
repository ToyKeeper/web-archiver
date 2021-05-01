#!/usr/bin/env python

import requests

#default_server = 'http://b.xyzz.org:4812/api/v1/submit'
default_server = 'http://localhost:4812/api/v1/submit'


def main(args):
    pass


def post(urls, server=None):
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

