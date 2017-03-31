#!/usr/bin/env bash

cd $(dirname $0)
basen=$(basename "$1" | cut -d. -f1)
source ../.venv/bin/activate
python $1 ${@:2} 2>&1 | logger -t $basen


