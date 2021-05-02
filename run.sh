#!/bin/sh
while true ; do
  date
  LANG=en_US.UTF8 $*
  sleep 1
done
