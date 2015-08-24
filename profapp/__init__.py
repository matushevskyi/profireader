from flask import Flask, session, g, request, redirect
from authomatic.providers import oauth2
from authomatic import Authomatic
from profapp.models.users import User
from profapp.controllers.blueprints import register as register_blueprints
from flask import url_for
from profapp.controllers.errors import csrf
from flask.ext.bootstrap import Bootstrap
from flask.ext.moment import Moment
from flask.ext.login import LoginManager, \
    login_user, logout_user, current_user, \
    login_required
from flask.ext.mail import Mail
import hashlib
from flask.ext.login import AnonymousUserMixin
from .constants.SOCIAL_NETWORKS import INFO_ITEMS_NONE, SOC_NET_FIELDS
from .constants.USER_REGISTERED import REGISTERED_WITH


def setup_authomatic(app):
    authomatic = Authomatic(app.config['OAUTH_CONFIG'],
                            app.config['SECRET_KEY'],
                            report_errors=True)
    def func():
        g.authomatic = authomatic
    return func


def load_user():
    user_init = current_user
    user = None

    user_dict = INFO_ITEMS_NONE.copy()
    user_dict['logged_via'] = None
    user_dict['registered_tm'] = None
    #  ['id', 'email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']

    if user_init.is_authenticated():
        id = user_init.get_id()
        user = User.query.filter_by(id=id).first()
        logged_via = REGISTERED_WITH[user.logged_in_via()]
        user_dict['logged_via'] = logged_via

        for attr in SOC_NET_FIELDS:
            if attr == 'link' or attr == 'phone':
                user_dict[attr] = \
                    str(user.attribute_getter(logged_via,  attr))
            else:
                user_dict[attr] = \
                    user.attribute_getter(logged_via,  attr)
        user_dict['id'] = id
        user_dict['registered_tm'] = user.registered_tm
        #name = user.user_name


    #user_dict = {'id': id, 'name': name, 'logged_via': logged_via}

    g.user_init = user_init
    g.user = user
    g.user_dict = user_dict
    g.delete = {'x': None}
    pass


#def load_user():
#    g.user = None
#    if 'user_id' in session.keys():
#        g.user = User.query.filter_by(id=session['user_id']).first()


def flask_endpoint_to_angular(endpoint, **kwargs):
    options = {}
    for kw in kwargs:
        options[kw] = "{{" + "{0}".format(kwargs[kw]) + "}}"
    url = url_for(endpoint, **options)
    import urllib.parse
    url = urllib.parse.unquote(url)
    url = url.replace('{{', '{{ ').replace('}}', ' }}')
    return url


mail = Mail()
moment = Moment()
bootstrap = Bootstrap()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
#  The login_view attribute sets the endpoint for the login page.
#  I am not sure that it is necessary
login_manager.login_view = 'auth.login'


class AnonymousUser(AnonymousUserMixin):
    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = hashlib.md5(
            'guest@profireader.com'.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def __repr__(self):
        return "<User(id = %r)>" % self.id

login_manager.anonymous_user = AnonymousUser



def create_app(config='config.ProductionDevelopmentConfig'):
    app = Flask(__name__)
    app.config.from_object(config)

    app.before_request(setup_authomatic(app))
    app.before_request(load_user)

    register_blueprints(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    login_manager.init_app(app)

    #if not app.debug and not app.testing and not app.config['SSL_DISABLE']:
    #    from flask.ext.sslify import SSLify
    #    sslify = SSLify(app)

    @login_manager.user_loader
    def load_user_manager(id):
        return User.query.get(id)

    csrf.init_app(app)

    # read this: http://stackoverflow.com/questions/6036082/call-a-python-function-from-jinja2
    app.jinja_env.globals.update(flask_endpoint_to_angular=flask_endpoint_to_angular)

    # see: http://flask.pocoo.org/docs/0.10/patterns/sqlalchemy/
    # Flask will automatically remove database sessions at the end of the
    # request or when the application shuts down:
    from db_init import db_session

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    return app
