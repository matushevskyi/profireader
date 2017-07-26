#!/bin/bash


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

function pause(){
   read -p "$*"
}

#localh="localhost/db1"
#remoteh="remotehost/db2"

if [ "$1" == "-h" ]
    then
    echo "$0 host1/db1/port1/user1/password1 host2/db2/port2/user2/password2"
    exit
fi

IFS='/' read -a Array <<< "$1"
localh="${Array[0]}"
localdb="${Array[1]}"
localport="${Array[2]}"
localuser="${Array[3]}"
localpass="${Array[4]}"

IFS='/' read -a Array <<< "$2"
remoteh="${Array[0]}"
remotedb="${Array[1]}"
remoteport="${Array[2]}"
remoteuser="${Array[3]}"
remotepass="${Array[4]}"

if [[ "$localport" == "" ]]; then
  localport='5432'
fi

if [[ "$remoteport" == "" ]]; then
  remoteport='5432'
fi

echo "comparing $localh/$localdb and $remoteh/$remotedb with additional parameters: $3"

#consolewidth=$(( $(tput cols) - 2 ))

#difffw="diff -wy --suppress-common-lines -W $consolewidth"

bakdir="/tmp"
scriptdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

date=`date +"%y_%m_%d___%H_%M"`
echo $date

localf="$bakdir/$localh""_$localdb""_schema_$date.sql"
remotef="$bakdir/$remoteh""_$remotedb""_schema_$date.sql"
localfdb="$bakdir/$localh""_$localdb""_$date.sql"
remotefdb="$bakdir/$remoteh""_$remotedb""_$date.sql"

function conf {
    # call with a prompt string or use a default
    read -r -p "${1:-Are you sure}? [Y/n]" response
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

echo "dump $localh/$localdb schema"
export PGPASSWORD=$localpass
pg_dump -s -U $localuser -h $localh --port=$localport $localdb $3 > $localf
ls -l1sh $localf
echo '--------------------------------------------------------------'
echo ''

echo "dump $remoteh/$remotedb schema"
export PGPASSWORD=$remotepass
pg_dump -s -U $remoteuser -h $remoteh --port=$remoteport $remotedb $3 > $remotef
ls -l1sh $remotef
echo '--------------------------------------------------------------'
echo ''

pause "change $remoteh/$remotedb->$localh/$localdb structure - sql to run on $remoteh/$remotedb in order to lead it to $localh/$localdb structure"
java -jar "$scriptdir/apgdiff-2.4.jar" $remotef $localf
echo '--------------------------------------------------------------'
echo ''

pause "change $localh/$localdb->$remoteh/$remotedb structure - sql to run on $localh/$localdb in order to lead it to $remoteh/$remotedb structure"
java -jar "$scriptdir/apgdiff-2.4.jar" $localf $remotef
echo '--------------------------------------------------------------'
echo ''



if conf "create local dump: dump $localh/$localdb full db"; then
    export PGPASSWORD=$localpass
    pg_dump -U $localuser -h $localh --port=$localport $localdb $3 > $localfdb
    ls -l1sh $localfdb
    echo '--------------------------------------------------------------'
    echo ''
fi

if conf "create remote dump: dump dump $remoteh/$remotedb full db"; then
    export PGPASSWORD=$remotepass
    pg_dump -U $remoteuser -h $remoteh --port=$remoteport $remotedb $3 > $remotefdb
    ls -l1sh $remotefdb
    echo '--------------------------------------------------------------'
    echo ''
fi

echo "copy $remoteh/$remotedb full db to $localh/$localdb SQL:"
echo ''
echo "run: 'echo \"ALTER DATABASE $localdb RENAME TO $localdb""_$date\" | psql -U $localuser -h $localh --port=$localport'"
echo "run: 'echo \"CREATE DATABASE $localdb OWNER $localuser TEMPLATE template1\" | psql -U $localuser -h $localh --port=$localport'"
echo "run: 'psql -U $localuser -h $localh --port=$localport $localdb < $remotefdb'"
echo '--------------------------------------------------------------'
echo ''

echo "copy $localh/$localdb full db to $remoteh/$remotedb SQL:"
echo ''
echo "run: 'echo \"ALTER DATABASE $remotedb RENAME TO $remotedb""_$date\" | psql -U $remoteuser -h $remoteh --port=$remoteport'"
echo "run: 'echo \"CREATE DATABASE $remotedb OWNER $remoteuser TEMPLATE template1\" | psql -U $remoteuser -h $remoteh --port=$remoteport'"
echo "run: 'psql -U $remoteuser -h $remoteh --port=$remoteport $remotedb < $localfdb'"
echo '--------------------------------------------------------------'
echo ''

