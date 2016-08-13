#!/bin/bash
httpdir=$1
maindomain=$2
aliases=$3

acertbot certonly --apache -n --agree-tos --email profireader@profireader.com  -w $httpdir -d $maindomain "${aliases[@]/#/-}"