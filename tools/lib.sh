#!/usr/bin/env bash

function db_name {
  cat ../scrt/secret_data.py | grep 'DB_NAME' | sed -e 's/^\s*DB_NAME\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g'
}

function db_user {
  cat ../scrt/secret_data.py | grep 'DB_USER' | sed -e 's/^\s*DB_USER\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g'
}

function db_pass {
  cat ../scrt/secret_data.py | grep 'DB_PASSWORD' | sed -e 's/^\s*DB_PASSWORD\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g'
}

function db_host {
  cat ../scrt/secret_data.py | grep 'DB_HOST' | sed -e 's/^\s*DB_HOST\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g'
}

function db_port {
  echo '5432'
#  cat ../scrt/secret_data.py | grep 'DB_PORT' | sed -e 's/^\s*DB_HOST\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g'
}

