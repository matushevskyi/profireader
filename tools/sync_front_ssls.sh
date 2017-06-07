#!/bin/bash

if [[ "$1" == '' ]]; then
  echo "usage: $0 httpdir_where_leth_encrypt_put_data_for_domain_ownership_validation main.domain [anoter.doamins... ]"
  exit
fi

httpdir=$1
maindomain=$2
args=($@)
aliases=("${args[@]:2}")




