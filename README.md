# profireader
Installation instruction:


In order to install psycopg2 in virtual environment you should install
libpq-dev python-dev packages first:
# sudo apt-get install libpq-dev python-dev

also you have to install 'python3-venv' package in order to work with Python 3
# sudo apt-get install python3-venv python3-pip

create new postgresql user 'pfuser':
$ sudo -u postgres createuser -D -A -P pfuser
(here system asks a password for just created user. Password can be found in
secret_data.py file as DB_PASSWORD constant)
# ALTER USER pfuser WITH PASSWORD '<newpassword>'

you need to add ip of db host (db.prof) to file /etc/hosts
If db is located on postgres.m server then its ip can be found with
`ping postgres.m` command. If db is located on localhost then ip is 0.0.0.0
Though, running `sudo gedit /etc/hosts` add following line:
ip    db.prof
where ip is a value derived on previous step.

we also have to add lines
0.0.0.0    profireader.com
to /etc/hosts

pfuser have to create new db named 'profireader'
# sudo -u postgres createdb -O pfuser profireader

to recover db from dump:
# su postgres
# psql profireader < dump.sql
# exit

virtual environment (on Python 3) with all necessary packages have to be created:
# pyvenv env && source env/bin/activate && pip3 install -r requirements.txt

to work with our DB you should install VPN. see instructions:
http://jira.ntaxa.com/browse/NTAXA-6

also you need to install file manager from bower package
# sudo apt-get install nodejs
# sudo apt-get install npm
# ln -s /usr/bin/nodejs /usr/bin/node
# npm install -g bower

install solr:
sudo apt-get -y install openjdk-7-jdk
mkdir /usr/java
ln -s /usr/lib/jvm/java-7-openjdk-amd64 /usr/java/default
wget http://download.nextag.com/apache/lucene/solr/5.3.0/solr-5.3.0.tgz
tar -zxvf solr-5.3.0.tgz


