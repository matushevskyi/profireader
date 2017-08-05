#!/bin/bash

sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:00 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=/root/vms/elk.profi.raw &
sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:10 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=/root/vms/postgres.profi.raw &
sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:11 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=/root/vms/elastic.profi.raw &
sleep 5
sudo ifup br10