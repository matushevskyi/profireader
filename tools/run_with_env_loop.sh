#!/usr/bin/env bash

cd $(dirname $0)
basen=$(basename "$2" | cut -d. -f1)
source ../.venv/bin/activate
while true
do
    python $2 ${@:3} 2>&1 | logger -t $basen
    echo "sleep 1+$1 seconds"
	sleep 1
	sleep $1
done
