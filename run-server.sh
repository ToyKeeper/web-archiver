#!/bin/sh
while true ; do
  date
  LANG=en_US.UTF8 ./server.py
  sleep 1
done
