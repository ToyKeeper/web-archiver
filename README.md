# Web Archiver

Ever wanted to save a copy of the pages you view?  Well, now you can.

## Overview

This archiver has two main parts:

  * **Server**: A very simple daemon which sits there waiting for URLs, and
    then downloads them.
  * **Clients**: One or more clients monitors the history files of various
    browsers, then sends new URLs to the server for archival.

The general idea is that you run an archive server somewhere on your network,
and run one client for each web browser on each computer you use.  In a simple
case, these can all be on the same computer.

## Server

The server listens on tcp port 4812 by default, and expects data to be sent in
json format via HTTP POST.  Load the server's front page in a browser for more
info.

It listens on all IP addresses by default, with no security or authentication
of any kind, so don't run this unless you're inside of a pretty safe firewall.

Files are archived to a directory hierarchy:

  * **~/.cache/web-archive/** : base directory
  * **basedir/YYYY/MM/DD/urls.log** : daily activity log
  * **basedir/YYYY/MM/DD/HH/** : archived data from pages viewed during this
    one-hour time period

If the same pages are viewed twice within the same hour, they'll be saved to
the same place.  Otherwise, a new copy is saved each time a URL is loaded.

However, downloads are rate-limited so it'll only download each URL once every
few minutes at most.  If you want to save a new copy, wait a few minutes and
hit 'reload' in the browser to trigger a new archive request.

The server listens for new URLs in a few different ways:

  * **HTTP** (primary listening method)
  * A **queue** file in the archiver's base directory.  Simply write URLs to
    the queue file, one per line, and it'll pick them up.  For example,
    `echo "http://example.com/" >> ~/.cache/web-archive/queue`
  * **stdin**: You can also just paste URLs into the terminal where the server
    is running. hit Enter, and it'll queue them up for archival.

## Clients

One client is needed per browser per host.

### Chrome client

Monitors Chrome's "History" file and sends new URLs to the server.

This History file is in sqlite3 format, and Chrome keeps a tight lock on that
file, and sqlite3 refuses to read from a locked database...  so the file must
be copied to a new temp file each time it's read.  This is rather unfortunate,
especially when the History file is large.

To minimize disk I/O, the file is only read if it's newer than the last
throw-away copy, and reads are rate-limited to a maximum of once per N seconds.
The speed is configurable in the config file.

It's also recommended that you delete your Chrome history once in a while to
avoid huge disk loads from copying it all the time.  Once a year is probably
sufficient in most cases.

### Dillo client

Dillo is a fast, very lightweight web browser.  It's great for quick queries
and "Web 1.0" style pages.  It doesn't have a history file though; it just
prints URLs to stdout.

So to detect URLs from Dillo, redirect output from your .Xsession into a log
file of some sort.  On many platforms, this happens by default and goes into
**$HOME/.xsession-errors** .  Then launch Dillo from a hotkey or menu in your
window manager, and it should log Dillo's output to the log file.

Alternately, you could run Dillo from a wrapper script which redirects its
output to a log file.

## Install

I doubt anyone except me is interested in using this, but just in case...

Requirements:

  * python3
  * python3-flask
  * python3-requests
  * python3-sqlite3 (included in python3 usually)
  * Linux or unix of some sort (I haven't attempted to make the program
    cross-platform)

To install, git clone the repository.  The files are designed to be run
in-place from wherever.

I'd recommend starting the clients from your .Xsession file or similar, so
they'll run whenever you're logged in.

## Configuration

For usage on a single computer, no configuration should be necessary.  The
defaults assume localhost and typical filesystem paths.

For something more complex though, make a config file...

```
mkdir ~/.web-archiver
cat > ~/.web-archiver/rc << EOF
server_url = 'http://myhost:4812/'
retry_time = 30

chrome_history_file = '/home/myuser/.config/chromium/Default/History'
chrome_polling_time = 10

dillo_logtail_path = '/home/myuser/.xsession-errors'
EOF
```
