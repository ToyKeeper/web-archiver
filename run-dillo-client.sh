#!/bin/sh
while true ; do
  date
  LANG=en_US.UTF8 ./dillo-client.py
  sleep 1
done
