import sys
import os, sys

sys.path.insert(0, '/var/www/profireader')
sys.path.insert(0, '/var/www/profireader/.venv/lib/python3.4/site-packages')

#sys.path.insert(0, '/var/www/profireader/.venv/lib/python3.4/site-packages/psycopg2')
#import _psycopg
#sys.modules['psycopg2._psycopg'] = _psycopg
#sys.path.pop(0)

#PROJECT_DIR = '/var/www/profireader'

#activate_this = os.path.join(PROJECT_DIR, 'bin', 'activate_this.py')
#execfile(activate_this, dict(__file__=activate_this))
#sys.path.append(PROJECT_DIR)

from profapp import create_app

application=create_app()

