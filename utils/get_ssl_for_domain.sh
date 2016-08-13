#!/bin/bash
httpdir=$1
maindomain=$2
args=($@)
aliases=("${args[@]:2}")
#("${A[@]:1}")
#acertbot
#echo $aliases
#echo ${aliases[@]}
certbot certonly --webroot -n --agree-tos --email profireader@profireader.com  -w $httpdir -d $maindomain "${aliases[@]/#/-d }"