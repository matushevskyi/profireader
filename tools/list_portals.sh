#!/bin/bash

. lib.sh

export PGPASSWORD=$(db_pass)
psql -U $(db_user) -h $(db_host) --port=$(db_port) -c "SELECT host,id,status FROM portal WHERE status = 'PORTAL_ACTIVE';" $(db_name)
