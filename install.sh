#!/bin/bash

rand=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)

PWD=$(pwd)

if [[ $(dpkg -l dialog | grep Version) == '' ]]; then
    sudo apt-get install dialog
fi

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
    command="wget --user='$ntaxauser' --password='$ntaxapass' -O /tmp/"$rand"tmpfile http://x.m.ntaxa.com/profireader/$filetoget
if [[ \"\$?\" == \"0\" ]]; then"
    if [[ "$3" != '' ]]; then
	command="$command
    mv $filetoput $filetobak"
    fi
    command="$command
    mv /tmp/"$rand"tmpfile $filetoput
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
	echo "$1" > /tmp/"$rand"menu_command_run_confirmed.sh
	if [[ "$2" == "sudo" ]]; then
	    sudo bash /tmp/"$rand"menu_command_run_confirmed.sh
	else
	    bash /tmp/"$rand"menu_command_run_confirmed.sh
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
    echo `cat secret_data.py | grep 'DB_NAME\s*=' | sed -e 's/^\s*DB_NAME\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `
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
apt-get install libpq-dev python-dev libapache2-mod-wsgi-py3 libjpeg-dev memcached" sudo npm
    }

function menu_npm {
    conf_comm "apt-get install nodejs
apt-get install npm
ln -s /usr/bin/nodejs /usr/bin/node 
npm install -g bower
npm install -g gulp" sudo bower
    }

function menu_bower {
    conf_comm "cd ./profapp/static
bower install" nosudo menu_bower_dev
    }

function menu_bower_dev {
    conf_comm "cd ./profapp/static/bower_components_dev
mkdir ./angular-db-filemanager
cd ./angular-db-filemanager
git clone git@github.com:kakabomba/angular-server-driven-filemanager.git .
cd ..
mkdir ./angular-crop
cd ./angular-crop
git clone git@github.com:kakabomba/ng-crop.git .
" nosudo hosts
    }

function menu_gulp {
     conf_comm "cd ./profapp/static
npm install gulp del gulp-less-sourcemap gulp-watch run-sequence gulp-task-listing
gulp" nosudo hosts
     }

function menu_hosts {
    conf_comm "sed -i '/\(db\|web\|mail\|memcached\|elastic\).profi/d' /etc/hosts
sed -i '/profireader.com/d' /etc/hosts
echo '' >> /etc/hosts
echo '127.0.0.1 db.profi web.profi mail.profi memcached.profi elastic.profi' >> /etc/hosts
echo '127.0.0.1 file001.profireader.com' >> /etc/hosts
echo '127.0.0.1 static.profireader.com' >> /etc/hosts
echo '127.0.0.1 profireader.com rodynni.firmy oles.profireader.com rodynnifirmy.profireader.com derevoobrobka.profireader.com viktor.profireader.com md.profireader.com oleh.profireader.com fsm.profireader.com' >> /etc/hosts
echo '127.0.0.1 test.profireader.com test1.profireader.com test2.profireader.com test3.profireader.com test4.profireader.com test5.profireader.com test6.profireader.com test7.profireader.com test8.profireader.com test9.profireader.com' >> /etc/hosts
cat /etc/hosts" sudo haproxy_compile
    }

function menu_haproxy_compile {
    conf_comm "apt-get purge haproxy
sed -i '/haproxy-1.5/d' /etc/apt/sources.list
echo '' >> /etc/apt/sources.list
echo 'deb http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main' >> /etc/apt/sources.list
echo 'deb-src http://ppa.launchpad.net/vbernat/haproxy-1.5/ubuntu trusty main' >> /etc/apt/sources.list
apt-get update
apt-get install haproxy" sudo haproxy_config
    }

function menu_haproxy_config {
    conf_comm "cp ./haproxy.cfg /etc/haproxy/
cp ./profireader_haproxy.key.pem /etc/haproxy/
service haproxy restart" sudo apache2_config
    }

function menu_apache2_config {
    conf_comm "cat profi-wsgi-apache2.conf | sed -e 's#----directory----#$PWD#g' > /etc/apache2/sites-enabled/profi-wsgi-apache2.conf
rm /etc/apache2/sites-available/000-default.conf
mkdir /var/log/profi
service apache2 restart" sudo secret_data
    }

function menu_secret_data {
    down secret_data.txt secret_data.py secret_data.`$gitv`_`$datev`.bak secret_client
    }

function menu_secret_client {
    down client_secret.json client_secret.json client_secret.json.`$gitv`_`$datev`.bak download_key_pem
    }

function menu_download_key_pem {
    down profireader_haproxy.key.pem profireader_haproxy.key.pem profireader_haproxy.key.pem profireader_haproxy.key.pem.`$gitv`_`$datev`.bak python_3
    }


function menu_python_3 {
    pversion=$(rr 'Enter python version' 3.4.2)
    destdir=$(rr 'destination dir' /usr/local/opt/python-$pversion)
    if [[ -e $destdir ]]; then
	echo "error: $destdir exists"
    else
#	warn_about_rm '/usr/bin/python3'
#	warn_about_rm '/usr/bin/pyvenv'
	conf_comm "cd /tmp/
rm -rf 'Python-$pversion/*'
rm 'Python-$pversion.tgz'
wget 'https://www.python.org/ftp/python/$pversion/Python-$pversion.tgz'
tar -zxf 'Python-$pversion.tgz'
cd 'Python-$pversion'
./configure --prefix='$destdir'
make
make install
cd /tmp
rm -rf 'Python-$pversion'" sudo venv
    fi
    }

function menu_venv {
    destdir=$(rr 'destination dir for virtual directory' .venv)
    pythondir=$(rr 'python dir' /usr/local/opt/python-3.4.2)
    if [[ -e $destdir ]]; then
	echo "error: $destdir exists"
    else
	conf_comm "$pythondir/bin/pyvenv $destdir
cp ./activate_this.py $destdir/bin" nosudo modules
    fi
    }

function menu_modules {
    req=$(rr 'file with modules' requirements.txt)
    destdir=$(rr 'venv directory' .venv)
    conf_comm "
cd `pwd`
source $destdir/bin/activate
pip3 install -I -r $req" nosudo bower_components_dev
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

makaronyaddress='m.ntaxa.com/profireader/54322'
localaddress='localhost/profireader/5432'
artekaddress='a.ntaxa.com/profireader/54321'

function menu_bower_components_dev {
    conf_comm "cd profapp/static/bower_components_dev
git clone git@github.com:kakabomba/angular-filemanager.git
cd angular-filemanager
git checkout ids" nosudo db_user_pass
    }

function menu_compare_local_makarony {
    conf_comm "./postgres.dump_and_compare_structure.sh $makaronyaddress $localaddress" nosudo compare_local_artek
    }

function menu_compare_local_artek {
    conf_comm "./postgres.dump_and_compare_structure.sh $localaddress $artekaddress" nosudo compare_makarony_artek
    }

function menu_compare_makarony_artek {
    conf_comm "./postgres.dump_and_compare_structure.sh $makaronyaddress $artekaddress" nosudo db_rename
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
    runsql_dump 'Enter sql full dump filename' database_full.sql db_reindex_search
    }

function menu_db_reindex_search {
    destdir=$(rr 'venv directory' .venv)
    conf_comm "
source $destdir/bin/activate
cd ./utils
python ./update_search_table.py
" nosudo 'db_reassign_ownership'
    }

function menu_db_reassign_ownership {

    profidb=$(get_profidb)

    profiuser=`cat secret_data.py | grep 'DB_USER' | sed -e 's/^\s*DB_USER\s*=\s*['"'"'"]\([^'"'"'"]*\).*$/\1/g' `

    conf_comm "
su postgres -c \"for tbl in \\\$(psql -qAt -c 'SELECT tablename      FROM pg_tables                     WHERE schemaname      = '\\\"'\\\"public\\\"'\\\"';' $profidb); do echo \\\$tbl; psql -c 'ALTER table \\\"'\\\$tbl'\\\" owner to $profiuser' $profidb ; done\"
su postgres -c \"for tbl in \\\$(psql -qAt -c 'SELECT sequence_name  FROM information_schema.sequences  WHERE sequence_schema = '\\\"'\\\"public\\\"'\\\"';' $profidb); do echo \\\$tbl; psql -c 'ALTER table \\\"'\\\$tbl'\\\" owner to $profiuser' $profidb ; done\"
su postgres -c \"for tbl in \\\$(psql -qAt -c 'SELECT table_name     FROM information_schema.views      WHERE table_schema    = '\\\"'\\\"public\\\"'\\\"';' $profidb); do echo \\\$tbl; psql -c 'ALTER table \\\"'\\\$tbl'\\\" owner to $profiuser' $profidb ; done\"
" sudo 'db_save_full'
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
"npm" "install nodejs, npm, bower and gulp globally" \
"bower" "download bower components in ./profapp/static/bower_components" \
"bower_dev" "download bower development components in ./profapp/static/bower_components_dev" \
"gulp" "install gulp in ./profapp/static" \
"hosts" "create virtual domain zone in /etc/hosts" \
"haproxy_compile" "compile and install haproxy" \
"haproxy_config" "copy haproxy config to /etc/haproxy" \
"apache2_config" "copy apache config to /etc/apache2 and allow currend dir" \
"secret_data" "download secret data" \
"secret_client" "download secret client data" \
"download_key_pem" "download https key and pem file" \
"python_3" "install python 3" \
"venv" "create virtual environment" \
"modules" "install required python modules (via pip)" \
"bower_components_dev" "get bower components (development version)" \
"db_user_pass" "create postgres user/password" \
"db_rename" "rename database (create backup)" \
"db_create" "create empty database" \
"db_save_minimal" "save initial database to file" \
"db_download_minimal" "get minimal database from x.m.ntaxa.com" \
"db_load_minimal" "load minimal database from file" \
"db_save_full" "save full database to file" \
"db_download_full" "get full database from x.m.ntaxa.com" \
"db_load_full" "load full database from file" \
"db_reindex_search" "reindex search table" \
"db_reassign_ownership" "reassign ownership" \
"compare_local_makarony" "compare local database and dev version" \
"compare_local_artek" "compare local database and production version" \
"compare_makarony_artek" "compare dev database and production version" \
"exit" "Exit" 2> /tmp/"$rand"selected_menu_
reset
datev="date +%y_%m_%d___%H_%M_%S"
gitv='git rev-parse --short HEAD'
menu_`cat /tmp/"$rand"selected_menu_`

done
