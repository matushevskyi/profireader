#!/usr/bin/env bash
source ../.venv/bin/activate
python ./$1 ${@:2} 1>>/var/log/profi/cron_`echo $1 | sed 's/.py$//g'`.log 2>>/var/log/profi/cron_`echo $1 | sed 's/.py$//g'`.error
