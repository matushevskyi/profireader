#!/bin/bash

sudo apt-get install dialog

function e {
    echo "$*"
    }

function menu_ {
    echo ''
    }

function ret {
    e
    read -p "Press [enter] to continue"
    e
    }


rr() {
    if [[ "$2" == "" ]]; then
      read -p "$1" retvalue
    else
      read -p "$1[$2]" retvalue
      if [[ "$retvalue" == "" ]]; then
	retvalue="$2"
      fi
    fi
    echo "$retvalue"
    }

function menu_exit {
    exit
    }

function conf {
    # call with a prompt string or use a default
    read -r -p "${1:-Are you sure? [Y/n]} " response
    if [[ "$response" == "" ]]; then
	true
    else 
    case $response in
        [yY][eE][sS]|[yY]) 
            true
            ;;
        *)
            false
            ;;
    esac
    fi
}

function down {
    filetoget=$1
    if [[ "$2" == "" ]]; then
	filetoput=${1##*/}
    else
	filetoput=$2
	
    fi

    filetobak="$3"

    ntaxauser=$(rr 'Enter ntaxa username:')
    ntaxapass=$(rr "Enter ntaxa password:")
    if [[ "$3" != '' ]]; then
	echo "  mv $filetoget $filetobak"
    fi
    command="wget --user='$ntaxauser' --password='$ntaxapass' -O /tmp/tmpfile http://x.d.ntaxa.com/profireader/$filetoget
if [[ \"\$?\" == \"0\" ]]; then"
    if [[ "$3" != '' ]]; then
	command="$command
    mv $filetoput $filetobak"
    fi
    command="$command
    mv /tmp/tmpfile $filetoput
else
    echo 'wget failed!'
fi"
    conf_comm "$command" nosudo $4
    }

conf_comm() {
rd=`tput setaf 1`
    rst=`tput sgr0`

    if [[ "$2" == "sudo" ]]; then
	echo "${rd}"
        echo "Command we're going to execute (with sudo):"
    else
	echo "Command we're going to execute:"
    fi
    e
    echo "$1" | sed -e 's/^/    /g'
    echo "${rst}"
    if conf; then
	e
	echo "$1" > /tmp/menu_command_run_confirmed.sh
	if [[ "$2" == "sudo" ]]; then
	    sudo bash /tmp/menu_command_run_confirmed.sh
	else
	    bash /tmp/menu_command_run_confirmed.sh
	fi
#        eval `echo "$1" | sed -e 's/"/\"/g' -e 's/^/sudo bash -c "/g' -e 's/$/";/g'`
	if [[ "$4" == "" ]]; then
	    ret
	fi
	if [[ "$3" != "" ]]; then
	    next="$3"
	fi
        true
    else
      false
    fi
}

function warn_about_rm {
    if [[ -e $1 ]]; then
    	    echo "warning: $1 exists and will be removed"
    fi
    }

function error_if_exists {
    if [[ -e $1 ]]; then
    	    echo "warning: $1 exists and will be removed"
    fi
    }

function get_profidb {
    echo `cat secret_data.py | grep 'DB_NAME' | sed -e 's/^\s*DB_NAME\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `
    }

function runsql {
    conf_comm "su postgres -c \"echo \\\"$1\\\" | psql\"" sudo "$2"
    }

function runsql_dump {
    profidb=$(get_profidb)
    filenam=$(rr "$1" "$2")
    conf_comm "su postgres -c 'cat $filenam | psql $profidb'" sudo "$3"
    }

function menu_origin {
    destination=`git remote -v | grep 'fetch' | sed -e 's/^.*github.com:\([^\/]*\)\/.*$/\1/g'`
    conf_comm "git remote rename origin $destination
git remote add origin git@github.com:kakabomba/profireader.git" nosudo postgres_9_4
    }

function menu_postgres_9_4 {
    conf_comm "echo 'deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main' >> /etc/apt/sources.list.d/pgdg.list
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | \
sudo apt-key add -
sudo apt-get update
apt-get install postgresql-9.4" sudo deb
    }

function menu_deb {
    conf_comm "apt-get update
apt-get install libpq-dev python-dev libapache2-mod-wsgi" sudo hosts
    }

function menu_hosts {
    conf_comm "sed -i '/\(db\|web\|mail\).profi/d' /etc/hosts
sed -i '/\(companyportal\|aprofi\).d.ntaxa.com/d' /etc/hosts
sed -i '/profi.ntaxa.com/d' /etc/hosts
echo '' >> /etc/hosts
echo '127.0.0.1 db.profi web.profi mail.profi' >> /etc/hosts
echo '127.0.0.1 profi.ntaxa.com oles.profi.ntaxa.com rodynnifirmy.profi.ntaxa.com derevoobrobka.profi.ntaxa.com viktor.profi.ntaxa.com aa.profi.ntaxa.com md.profi.ntaxa.com oleh.profi.ntaxa.com file001.profi.ntaxa.com fsm.profi.ntaxa.com' >> /etc/hosts
echo '127.0.0.1 test.profi.ntaxa.com test1.profi.ntaxa.com test2.profi.ntaxa.com test3.profi.ntaxa.com test4.profi.ntaxa.com test5.profi.ntaxa.com test6.profi.ntaxa.com test7.profi.ntaxa.com test8.profi.ntaxa.com test9.profi.ntaxa.com' >> /etc/hosts
cat /etc/hosts" sudo haproxy
    }

function menu_haproxy {
    conf_comm "apt-get purge haproxy
sed -i '/haproxy-1.5/d' /etc/apt/sources.list
echo '' >> /etc/apt/sources.list
echo 'deb http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main' >> /etc/apt/sources.list
echo 'deb-src http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main' >> /etc/apt/sources.list
apt-get update
apt-get install haproxy
cp ./haproxy.cfg /etc/haproxy/
service haproxy restart" sudo secret_data
    }

function menu_secret_data {
    down secret_data.txt secret_data.py secret_data.`$gitv`_`$datev`.bak secret_client
    }

function menu_secret_client {
    down client_secret.json client_secret.json client_secret.json.`$gitv`_`$datev`.bak python_3
    }

function menu_python_3 {
    pversion=$(rr 'Enter python version' 3.4.2)
    destdir=$(rr 'destination dir' /usr/local/opt/python-$pversion)
    if [[ -e $destdir ]]; then
	echo "error: $destdir exists"
    else
	warn_about_rm '/usr/bin/python3'
	warn_about_rm '/usr/bin/pyvenv'
	conf_comm "cd /tmp/
rm -rf 'Python-$pversion/*'
rm 'Python-$pversion.tgz'
wget 'https://www.python.org/ftp/python/$pversion/Python-$pversion.tgz'
tar -zxf 'Python-$pversion.tgz'
cd 'Python-$pversion'
./configure --prefix='$destdir'
make
make install
rm /usr/bin/python3
rm /usr/bin/pyvenv
ln -s $destdir/bin/python3 /usr/bin/python3
ln -s $destdir/bin/pyvenv /usr/bin/pyvenv
cd /tmp
rm -rf 'Python-$pversion'" sudo venv
    fi
    }

function menu_venv {
    destdir=$(rr 'destination dir for virtual directory' .venv)
    if [[ -e $destdir ]]; then
	echo "error: $destdir exists"
    else
	conf_comm "pyvenv $destdir" nosudo modules
    fi
    }

function menu_modules {
    req=$(rr 'file with modules' requirements.txt)
    destdir=$(rr 'venv directory' .venv)
    conf_comm "
cd `pwd`
source $destdir/bin/activate
pip3 install -r $req" nosudo port
    }

function menu_port {
    toport=$(rr 'redirect port 80 to port' 8080)
    conf_comm "iptables -t nat -A OUTPUT  -d 127.0.0.1  -p tcp --dport 80 -j REDIRECT --to-port $toport" sudo db_user_bass
    }

function menu_db_user_pass {
    echo "Going to create user/pass from secret data and create such user/pass using postgres user"
    echo "If user exists, only password will be changed"
    
    profiuser=`cat secret_data.py | grep 'DB_USER' | sed -e 's/^\s*DB_USER\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `
    psqluser=$(rr 'Enter postgresql user' $profiuser)
    
    profipass=`cat secret_data.py | grep 'DB_PASSWORD' | sed -e 's/^\s*DB_PASSWORD\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `
    psqlpass=$(rr 'Enter postgresql password' $profipass)
    runsql "CREATE USER $psqluser;
ALTER USER $psqluser WITH PASSWORD '$psqlpass';" compare_local_makarony
    }


function menu_compare_local_makarony {
    conf_comm "./postgres.dump_and_compare_structure.sh localhost/profireader/5432 d.ntaxa.com/profireader/54321" nosudo compare_local_artek
    }

function menu_compare_local_artek {
    conf_comm "./postgres.dump_and_compare_structure.sh localhost/profireader/5432 a.ntaxa.com/profireader/54321" nosudo compare_makarony_artek
    }

function menu_compare_makarony_artek {
    conf_comm "./postgres.dump_and_compare_structure.sh d.ntaxa.com/profireader/54321 a.ntaxa.com/profireader/54321" nosudo db_rename
    }

function menu_db_rename {
    profidb=$(get_profidb)
    runsql "ALTER DATABASE $profidb RENAME TO bak_$profidb""_"`$gitv`"_"`$datev` 'db_create'
    }

function menu_db_create {
    profidb=$(get_profidb)
    psqldb=$(rr 'Enter postgresql database name' $profidb)
    
    profiuser=`cat secret_data.py | grep 'DB_USER' | sed -e 's/^\s*DB_USER\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `
    runsql "CREATE DATABASE $psqldb WITH ENCODING 'UTF8' LC_COLLATE='C.UTF-8' LC_CTYPE='C.UTF-8'  OWNER = $profiuser TEMPLATE=template0" db_download_minimal
    }


function menu_db_download_minimal {
    down database.structure database.structure database.structure.`$gitv`_`$datev`.bak db_load_minimal
    }

function menu_db_load_minimal {
    runsql_dump 'Enter sql structure filename' database.structure db_save_minimal
    }

function menu_db_save_minimal {
    profidb=$(get_profidb)
    conf_comm "
su postgres -c 'pg_dump -s $profidb' > database.structure
tables=\$(su postgres -c \"echo 'SELECT RelName FROM pg_Description JOIN pg_Class ON pg_Description.ObjOID = pg_Class.OID WHERE ObjSubID = 0 AND Description LIKE '\\\"'\\\"%persistent%\\\"'\\\" | psql -t $profidb\" | sed '/^\\s*\$/d' | sed -e 's/^/-t /g' | tr \"\\n\" \" \" )
su postgres -c \"pg_dump --inserts -a \$tables $profidb\" >> database.structure
git diff database.structure" sudo 'db_download_full'
    }

function menu_db_download_full {
    down database_full.sql database_full.sql database_full.sql.`$gitv`_`$datev`.bak db_load_full
    }

function menu_db_load_full {
    runsql_dump 'Enter sql full dump filename' database_full.sql db_save_full
    }


function menu_db_save_full {
    profidb=$(get_profidb)
    conf_comm "
mv database_full.sql database_full.sql."`$gitv`"_"`$datev`".bak
su postgres -c 'pg_dump $profidb' > database_full.sql
ls -l1sh database_full.*
" sudo 'exit'
    }


next='_'

#a="/bin/ls;
#/bin/ls"

#eval $a

#exit

while :
do
#next='exit'
dialog --title "profireader" --nocancel --default-item $next --menu "Choose an option" 22 78 17 \
"origin" "change git origin and add new remote repo" \
"postgres_9_4" "install postgres 9.4" \
"deb" "install deb packages" \
"hosts" "create virtual domain zone in /etc/hosts" \
"haproxy" "install haproxy" \
"secret_data" "download secret data" \
"secret_client" "download secret client data" \
"python_3" "install python 3" \
"venv" "create virtual environment" \
"modules" "install required python modules (via pip)" \
"port" "redirect port at localhost 80->8080" \
"db_user_pass" "create postgres user/password" \
"db_rename" "rename database (create backup)" \
"db_create" "create empty database" \
"db_save_minimal" "save initial database to file" \
"db_download_minimal" "get minimal database from x.d.ntaxa.com" \
"db_load_minimal" "load minimal database from file" \
"db_save_full" "save full database to file" \
"db_download_full" "get full database from x.d.ntaxa.com" \
"db_load_full" "load full database from file" \
"compare_local_makarony" "compare local database and dev version" \
"compare_local_artek" "compare local database and production version" \
"compare_makarony_artek" "compare dev database and production version" \
"exit" "Exit" 2> /tmp/selected_menu_
reset
datev="date +%y_%m_%d___%H_%M_%S"
gitv='git rev-parse --short HEAD'
menu_`cat /tmp/selected_menu_`

done
