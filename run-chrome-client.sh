#!/bin/sh
while true ; do
  date
  LANG=en_US.UTF8 ./chrome-client.py
  sleep 1
done
