#!/bin/bash

source .venv/bin/activate

while [[ true ]]; do
    sleep 1
    echo "starting $1"
    python run.py $1 >> /var/log/profi/"$1"_python.log 2>&1
done

