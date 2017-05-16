#!/usr/bin/env bash

ansible-playbook  -vv -l profi -i ./a/inventories/profi.py -s $1 --extra-vars="${@:2}"