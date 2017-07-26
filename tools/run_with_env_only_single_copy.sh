#!/usr/bin/env bash

cd $(dirname $0)
mkdir -p /var/run/profi
basen=$(basename "$1" | cut -d. -f1)
pid_file="/var/run/profi/$basen.pid"
if [ -f $pid_file ]; then
  echo "currently running under pid $(cat $pid_file). you can try: kill -9 $(cat $pid_file)"
else
  ./run_with_env.sh $1 ${@:2} &
  pid=$!
  echo $pid>$pid_file
  wait $pid
  rm $pid_file
fi

