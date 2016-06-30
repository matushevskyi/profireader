#!/bin/bash

s='elastic.profi:9200'

curl -XPUT "$s/article?pretty"
curl "$s/_cat/indices?v"

