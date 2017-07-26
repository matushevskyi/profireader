#!/bin/bash

cd /var/www/
source .venv/bin/activate
python run.py socket >> /var/log/profi/socket-error.log


