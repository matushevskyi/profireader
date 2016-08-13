import os
import mod_wsgi

curdir = os.path.dirname(os.path.realpath(__file__))
print('curdir = ' + curdir )

# activate_this = curdir + '/.venv/bin/activate_this.py'
# print('activate_this = ' + activate_this)
# exec(open(activate_this).read())

import sys

# path = os.path.join(os.path.dirname(__file__), os.pardir)
# if path not in sys.path:
#     sys.path.append(path)


if not curdir + '/' in sys.path:
    sys.path.insert(0, curdir + '/')
    sys.path.insert(0, curdir + '/.venv/lib/python3.4/site-packages/')

# sys.path = [curdir + '/', curdir + '/.venv/lib/python3.4/site-packages/', '/usr/local/opt/python-3.4.2/lib/python3.4/']

print('!' + sys.version + '!')

print(sys.path)

from profapp import create_app

print(mod_wsgi.process_group)

application=create_app(apptype = mod_wsgi.process_group)
