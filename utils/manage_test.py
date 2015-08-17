# install into environment 'future' package (see requirements.txt)
# It works as for Py2 as for Py3!!!
#
# http://python-future.org/quickstart.html
# see 'Installation' section
#
# The easiest way to write code valid for both Py2 and Py3 is
# to start each new module with these lines:
from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *
from future import standard_library
standard_library.install_aliases()
# see also:
# http://python-future.org/what_else.html#what-else

from flask import url_for
from flask.ext.script import Manager
# for making scripts with Flask see documentation:
# http://flask-script.readthedocs.org/en/latest/

from profapp import create_app, flask_endpoint_to_angular

app = create_app()
manager = Manager(app)

@manager.command
def list_routes():
    import urllib.parse
    output = []
    st = '{:30s} {:25s} {:35s} {}'
    for rule in app.url_map.iter_rules():
        print(rule.rule)
        print(rule.arguments)
        print(rule.endpoint)
        methods = ','.join(rule.methods)
        options = {}
        for arg in rule.arguments:
            options[str(arg)] = "{{" + "{0}".format(str(arg)) + "}}"
        options['{{XXX'] = 'YYY}}'
        options['{{VVV'] = 'UUU}}'
        print(options)
        print("**************************")
        try:
            with app.app_context():
                # see this:
                # http://flask.pocoo.org/docs/0.10/config/ (SERVER_NAME variable)
                # and this:
                # http://kronosapiens.github.io/blog/2014/08/14/understanding-contexts-in-flask.html
                # we also have to add line
                # 0.0.0.0    profireader.a
                # to /etc/hosts
                url = url_for(rule.endpoint, **options)
                kwargs = {'soc_network_name': 'google'}
                url = flask_endpoint_to_angular('auth.login_soc_network', **kwargs)
                print(url)
                pass
        except ValueError:
            url = None
        line = urllib.parse.unquote(
            st.format(rule.endpoint, methods, str(rule), url)
        )
        output.append(line)

    for line in sorted(output):
        print(line)

list_routes()
