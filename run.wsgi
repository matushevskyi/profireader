import os
import sys
import mod_wsgi

curdir = os.path.dirname(os.path.realpath(__file__))

activate_this = curdir + '/.venv/bin/activate_this.py'
exec(open(activate_this).read())

path = os.path.join(os.path.dirname(__file__), os.pardir)
if path not in sys.path:
    sys.path.append(path)

sys.path.insert(0, curdir + '/')
sys.path.insert(0, curdir + '/.venv/lib/python3.4/site-packages/')

from profapp import create_app

print(mod_wsgi.process_group)

application=create_app(apptype = mod_wsgi.process_group)

