#!/bin/bash

su postgres -c "cd ~; psql -c 'SELECT host,id,status FROM portal WHERE status = '\''PORTAL_ACTIVE'\'';' profireader"

