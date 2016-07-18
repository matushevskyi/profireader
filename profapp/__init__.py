import hashlib
import re
from flask import Flask, g, request, current_app, session
from authomatic import Authomatic
from flask.ext.bootstrap import Bootstrap
from flask.ext.login import LoginManager, current_user, AnonymousUserMixin
from flask.ext.mail import Mail

from profapp.controllers.errors import csrf
from .constants.SOCIAL_NETWORKS import INFO_ITEMS_NONE, SOC_NET_FIELDS
from .constants.USER_REGISTERED import REGISTERED_WITH
from .models.users import User
from config import Config
from .models.config import Config as ModelConfig
from profapp.controllers.errors import BadDataProvided
import os.path
from profapp import utils
from flask.sessions import SessionInterface
from beaker.middleware import SessionMiddleware
from .utils.jinja_utils import update_jinja_engine, get_url_adapter


def req(name, allowed=None, default=None, exception=True):
    ret = request.args.get(name)
    if allowed and (ret in allowed):
        return ret
    elif default is not None:
        return default
    elif exception:
        raise Exception("value `{}` is not among allowed `{}`".format(name, allowed))
    else:
        return None


def db_session_func(db_config):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import scoped_session, sessionmaker

    engine = create_engine(db_config, echo=False)
    g.sql_connection = engine.connect()

    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
    # from sqlalchemy.orm import Session
    # strong_reference_session(Session())
    return db_session


def load_database(db_config):
    def load_db():
        db_session = db_session_func(db_config)
        g.db = db_session
        g.req = req
        g.filter_json = utils.filter_json
        g.get_url_adapter = get_url_adapter
        g.fileUrl = utils.fileUrl

    return load_db


def close_database(exception):
    db = getattr(g, 'db', None)
    sql_connection = getattr(g, 'sql_connection', None)
    if sql_connection:
        sql_connection.close()
    if db is not None:
        if exception:
            db.rollback()
        else:
            db.commit()
            db.close()


def setup_authomatic(app):
    authomatic = Authomatic(app.config['OAUTH_CONFIG'],
                            app.config['SECRET_KEY'],
                            report_errors=True)

    def func():
        g.authomatic = authomatic

    return func


def load_user(apptype):
    g.user = current_user if current_user.is_authenticated() else None


    lang = session['language'] if 'language' in session else 'uk'
    g.lang = g.user.lang if g.user else lang
    g.languages = Config.LANGUAGES

    g.portal = None
    g.portal_id = None
    g.portal_layout_path = ''

    g.debug = current_app.debug
    g.testing = current_app.testing

    for variable in g.db.query(ModelConfig).filter_by(server_side=1).all():
        var_id = variable.id
        if variable.type == 'int':
            current_app.config[var_id] = int(variable.value)
        elif variable.type == 'bool':
            current_app.config[var_id] = False if int(variable.value) == 0 else True
        else:
            current_app.config[var_id] = '%s' % (variable.value,)


mail = Mail()
bootstrap = Bootstrap()

login_manager = LoginManager()
login_manager.session_protection = 'strong'
#  The login_view attribute sets the endpoint for the login page.
#  I am not sure that it is necessary
login_manager.login_view = 'auth.login_signup_endpoint'


class AnonymousUser(AnonymousUserMixin):
    id = 0

    avatar = {
        'url': ''
    }

    @staticmethod
    def check_rights(permissions):
        return False

    @staticmethod
    def is_administrator():
        return False

    def get_id(self):
        return self.id

    @staticmethod
    @property
    def user_name():
        return 'Guest'

    def get_avatar(self, size=100):
        avatar = self.gravatar(size=size)
        return avatar

    def gravatar(self, size=100, default='identicon', rating='g'):
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url='https://secure.gravatar.com/avatar' if request.is_secure else 'http://www.gravatar.com/avatar',
            hash=hashlib.md5(getattr(self, 'address_email', 'guest@' + Config.MAIN_DOMAIN).encode('utf-8')).hexdigest(),
            size=size, default=default, rating=rating)

    def __repr__(self):
        return "<User(id = %r)>" % self.id


login_manager.anonymous_user = AnonymousUser


def create_app(config='config.ProductionDevelopmentConfig', apptype='profi'):
    app = Flask(__name__, static_folder='./static')

    app.config.from_object(config)

    app.teardown_request(close_database)

    app.debug = app.config['DEBUG'] if 'DEBUG' in app.config else False
    app.testing = app.config['TESTING'] if 'TESTING' in app.config else False

    app.before_request(load_database(app.config['SQLALCHEMY_DATABASE_URI']))
    app.before_request(lambda: load_user(apptype))
    app.before_request(setup_authomatic(app))

    def add_map_headers_to_less_files(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        if request.path and re.search(r'\.css$', request.path):
            mapfile = re.sub(r'\.css$', r'.css.map', request.path)
            if os.path.isfile(os.path.realpath(os.path.dirname(__file__)) + mapfile):
                response.headers.add('X-Sourcemap', mapfile)
        return response

    app.after_request(add_map_headers_to_less_files)

    if apptype == 'front':

        # relative paths
        def join_path(template, parent):
            return os.path.join(os.path.dirname(parent), template)

        app.jinja_env.join_path = join_path

        def load_portal():
            from profapp.models.portal import Portal
            portal = g.db.query(Portal).filter_by(host=request.host).first()
            g.portal = portal if portal else None
            g.portal_id = portal.id if portal else None
            g.portal_layout_path = portal.layout.path if portal else ''
            g.lang = g.portal.lang if g.portal else g.user_dict['lang'] if portal else 'en'

        app.before_request(load_portal)
        from profapp.controllers.blueprints_register import register_front as register_blueprints_front
        register_blueprints_front(app)

    elif apptype == 'static':
        from profapp.controllers.blueprints_register import register_static as register_blueprints_static
        register_blueprints_static(app)
    elif apptype == 'file':
        from profapp.controllers.blueprints_register import register_file as register_blueprints_file
        register_blueprints_file(app)
    else:
        from profapp.controllers.blueprints_register import register_profi as register_blueprints_profi
        register_blueprints_profi(app)

    bootstrap.init_app(app)
    mail.init_app(app)
    # moment.init_app(app)
    login_manager.init_app(app)
    login_manager.session_protection = 'basic'

    @login_manager.user_loader
    def load_user_manager(user_id):
        return g.db.query(User).get(user_id)

    update_jinja_engine(app)

    session_opts = {
        'session.type': 'ext:memcached',
        'session.url': 'memcached.profi:11211'
    }

    class BeakerSessionInterface(SessionInterface):
        def open_session(self, app, request):
            _session = request.environ['beaker.session']
            return _session

        def save_session(self, app, session, response):
            session.save()

    app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
    app.session_interface = BeakerSessionInterface()

    return app

