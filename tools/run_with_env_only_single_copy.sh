#!/usr/bin/env bash

basen=$(echo $1 | sed 's/.py$//g')

if [ ! -d '/run/profi' ]; then
  mkdir '/run/profi'
fi

pidfile="/run/profi/$basen.pid"

if [ -f $pidfile ]; then
  (>&2 echo "Error. pid file $pidfile exists.
  kill -9  $(cat $pidfile)
  rm $pidfile")
  exit
fi
echo "Starting work $1"
START=$(date +%s)
source ../.venv/bin/activate && echo $$ > $pidfile && python ./$1 ${@:2}
if [[ "$?" != "0" ]]; then
  echo "Error occurred"
fi
rm $pidfile
END=$(date +%s)
DIFF=$(( $END - $START ))
echo "It took $DIFF seconds"

