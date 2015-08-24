# profireader
Installation instruction:

In order to install psycopg2 in virtual environment you should install
libpq-dev python-dev packages first:
$ sudo apt-get install libpq-dev python-dev

also you have to install 'python3-venv' package in order to work with Python 3
$ sudo apt-get install python3-venv python3-pip

create new postgresql user 'pfuser':
$ sudo -u postgres createuser -D -A -P pfuser
(here system asks a password for just created user. Password can be found in
secret_data.py file as DEV_DB_PASSWORD constant)
#ALTER USER pfuser WITH PASSWORD '<newpassword>'

you need to add ip of db host (db.prof) to file /etc/hosts
If db is located on postgres.d server then its ip can be found with
`ping postgres.d` command. If db is located on localhost then ip is 0.0.0.0
Though, running `mcedit /etc/hosts` add following line:
ip    db.prof
where ip is a value derived on previous step.

we also have to add lines
0.0.0.0    profireader.a
to /etc/hosts

pfuser have to create new db named 'profireader'
$ sudo -u postgres createdb -O pfuser profireader

virtual environment (on Python 3) with all necessary packages
have to be created:
$ pyvenv env && source env/bin/activate && pip3 install -r requirements.txt

(if you want to create a virtual environment on Python 2 run the following:
$ virtualenv env2 && . env2/bin/activate && pip install -r requirements.txt )

also you need to install file manager from bower package
$sudo apt-get install nodejs
$sudo apt-get install npm
$ln -s /usr/bin/nodejs /usr/bin/node
$npm install -g bower
