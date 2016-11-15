#!/usr/bin/env bash

basen = $(echo $1 | sed 's/.py$//g')

source ../.venv/bin/activate

python ./$1 ${@:2} 1>>/var/log/profi/$basen.log 2>>/var/log/profi/$basen.error

