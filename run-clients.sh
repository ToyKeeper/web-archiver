#!/bin/sh

CLIENTS="dillo chrome"

# kill old processes
for client in $CLIENTS ; do
  for pid in $(
    ps axu \
      | grep "$client"-client.py \
      | egrep 'run.sh|python' \
      | awk '{ print $2 }'
    ) ; do
    kill $pid
  done
done

sleep 1

# start new processes
cd $(dirname "$0")
for client in $CLIENTS ; do
  ./run.sh ./"$client"-client.py > /dev/null &
done
