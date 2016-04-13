![GitHub Logo](http://i63.tinypic.com/1zvuyx4_th.png)
<br><br><br>

###**Installation instruction:**
>*    1.)Install required package libs:
<br />sudo apt-get install libpq-dev python-dev
      sudo apt-get install python3-venv python3-pip
<br />
>*    2:)Create new postgresql user 'pfuser':
<br />sudo -u postgres createuser -D -A -P pfuser
      (here system asks a password for just created user. Password can be found in
       secret_data.py file as DB_PASSWORD constant)
      ALTER USER pfuser WITH PASSWORD '<newpassword>'
<br />
>*    3:)Modify /etc/hosts file:
<br />you need to add ip of db host (db.prof) to file /etc/hosts
      If db is located on postgres.m server then its ip can be found with
      `ping postgres.m` command. If db is located on localhost then ip is 0.0.0.0
      Though, running `sudo gedit /etc/hosts` add following line:
      ip    db.prof
      where ip is a value derived on previous step.
      we also have to add lines
      0.0.0.0    profireader.com
      to /etc/hosts
<br />
>*    4:)Create new db "profireader":
<br />sudo -u postgres createdb -O pfuser profireader
      to recover db from dump:
      su postgres
      psql profireader < dump.sql
      exit
<br />
>*    5:)Install virtual environment and necessary packages:
<br />pyvenv env && source env/bin/activate && pip3 install -r requirements.txt
<br />
>*    6:)To work with your local DB you should install VPN. see instructions:
<br />[Click here for instructions](http://jira.ntaxa.com/browse/NTAXA-6)
<br />
>*    7:)Install file manager from bower package:
<br />sudo apt-get install nodejs
      sudo apt-get install npm
      ln -s /usr/bin/nodejs /usr/bin/node
      npm install -g bower
