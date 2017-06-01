#!/usr/bin/env bash

extra_vars="${@:2}"


ansible-playbook  -vv --vault-password-file=../../../.ansible_vault_pass.txt -l profi -i ./a/inventories/profi.py -s $1 --extra-vars="$extra_vars"
#ansible-playbook  -vv --vault-password-file=../../../.ansible_vault_pass.txt -s $1 --extra-vars="${@:2}"