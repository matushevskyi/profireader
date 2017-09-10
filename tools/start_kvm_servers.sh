#!/bin/bash

#apt-get install bridge-utils uml-utilities

srv="/srv/profi"
/usr/local/bin/ntaxa-run-kvm.sh $srv/elk.profi.raw -display none &
/usr/local/bin/ntaxa-run-kvm.sh $srv/postgres.profi.raw -display none &
/usr/local/bin/ntaxa-run-kvm.sh $srv/elastic.profi.raw -display none &
#sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:00 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=$srv/elk.profi.raw &
#sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:10 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=$srv/postgres.profi.raw &
#sudo kvm ${@:1} -m 1024 -device e1000,netdev=net10,mac=00:10:01:01:01:11 -netdev tap,id=net10,script=/root/create_tun.sh -drive format=raw,file=$srv/elastic.profi.raw &
#sleep 5
#sudo ifup br10
