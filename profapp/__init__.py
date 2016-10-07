import hashlib
import re
from flask import Flask, g, request, current_app, session
from authomatic import Authomatic
from flask.ext.bootstrap import Bootstrap
from flask.ext.login import LoginManager, current_user, AnonymousUserMixin
from flask.ext.mail import Mail

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
import json


def req(name, allowed=None, default=None, exception=True):
    ret = request.args.get(name)
    if allowed is None or (ret in allowed):
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

    # lang = session['language'] if 'language' in session else 'uk'
    g.languages = Config.LANGUAGES

    g.lang = 'en'
    if 'HTTP_ACCEPT_LANGUAGE' in request.headers.environ:
        agent_languages = list(map(lambda l: re.compile("\s*;\s*q=").split(l),
                                   re.compile("\s*,\s*").split(request.headers.environ['HTTP_ACCEPT_LANGUAGE'])))
        agent_languages.sort(key=lambda x: float(x[1]) if len(x) > 1 else 1, reverse=True)
        for lng in agent_languages:
            if lng[0][0:2] in [l['name'] for l in g.languages]:
                g.lang = lng[0][0:2]
                break
    if g.user:
        g.lang = g.user.lang
    if 'language' in session:
        g.lang = session['language']

    if g.lang not in [l['name'] for l in g.languages]:
        g.lang = 'en'
    # = g.user.lang if g.user else lang


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

    @login_manager.user_loader
    def load_user_manager(user_id):
        return g.db.query(User).get(user_id)

    # if apptype in ['file', 'profi', 'static', 'front']:

    session_opts = {
        'session.type': 'ext:memcached',
        'session.cookie_domain': '.' + Config.MAIN_DOMAIN,
        'session.url': 'memcached.profi:11211'
    }

    class BeakerSessionInterface(SessionInterface):
        def open_session(self, app, request):
            return request.environ.get('beaker.session')

        def save_session(self, app, session, response):
            session.save()

    app.wsgi_app = SessionMiddleware(app.wsgi_app, session_opts)
    app.session_interface = BeakerSessionInterface()

    app.type = apptype
    login_manager.init_app(app)
    login_manager.session_protection = 'basic'

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
        update_jinja_engine(app)

    elif apptype == 'static':
        from profapp.controllers.blueprints_register import register_static as register_blueprints_static
        register_blueprints_static(app)
    elif apptype == 'file':
        from profapp.controllers.blueprints_register import register_file as register_blueprints_file
        register_blueprints_file(app)
    elif apptype == 'socket':

        # from flask_socketio import SocketIO, emit
        # socketio = SocketIO(app)
        #
        # @socketio.on('connect')
        # def connect_handler():
        #     print(current_user)
        #     if current_user.is_authenticated:
        #         emit('my response',
        #              {'message': '{0} has joined'.format(current_user.name)},
        #              broadcast=True)
        #     else:
        #         return False  # not allowed here
        #
        # socketio.run(app)


        # from sqlalchemy import create_engine
        from config import database_uri
        import select
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        import psycopg2
        import psycopg2.extensions
        import socketio, eventlet

        conn = psycopg2.connect(dbname=Config.database, user=Config.username, password=Config.password,
                                host=Config.host)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        conn.autocommit = True
        curs = conn.cursor()

        sio = socketio.Server(cookie='prsio')

        sid2userid = {}
        userid2seeds = {}

        def check_user_id(environ):
            session_id = environ.get('HTTP_COOKIE', None)
            if not session_id:
                return False
            session_id = re.sub(r'^(.*;\s*)?beaker\.session\.id=([0-9a-f]*).*$', r'\2', session_id)
            import memcache
            mc = memcache.Client(['memcached.profi:11211'], debug=0)
            session = mc.get(session_id + '_session')
            return session.get('user_id', False) if session else False

        @sio.on('connect')
        def connect(sid, environ):
            user_id = check_user_id(environ)
            if not user_id:
                return False
            sid2userid[sid] = [user_id, None]

            if not user_id in userid2seeds:
                userid2seeds[user_id] = []
                chanel = user_id.replace('-', '_')
                print("Waiting for notifications on channel new_message_to_user___" + chanel)
                curs.execute("LISTEN new_message_to_user___%s;" % (chanel,))
                curs.execute("LISTEN message_read_user___%s;" % (chanel,))

            userid2seeds[user_id].append(sid)
            sio.enter_room(sid, 'set_unread_message_count-' + user_id)

        @sio.on('disconnect')
        def disconnect(sid):
            (user_id, selected_chat_room_id) = tuple(sid2userid[sid])
            del sid2userid[sid]
            userid2seeds[user_id].remove(sid)
            if not len(userid2seeds[user_id]):
                chanel = user_id.replace('-', '_')
                print("DON`T Waiting for notifications on channel new_message_to_user___" + chanel)
                curs.execute("UNLISTEN new_message_to_user___%s;" % (chanel,))
                curs.execute("UNLISTEN message_read_user___%s;" % (chanel,))
                del userid2seeds[user_id]

        @sio.on('select_chat_room_id')
        def select_chat_room(sid, message):
            print('---select_chat_room_id', sid, message)
            sid2userid[sid][1] = message['select_chat_room_id']
            pass

        def get_cnt(user_id):
            print('get_cnt', user_id)
            curs.execute("SELECT contact.id, COUNT(contact.id) as cnt FROM contact LEFT JOIN "
                         "message ON (message.contact_id = contact.id AND message.read_tm IS NULL AND message.to_user_id = '%s')"
                         "WHERE (message.id IS NOT NULL AND (contact.user1_id = '%s' OR contact.user2_id = '%s'))"
                         "GROUP BY contact.id" % (user_id, user_id, user_id))
            ret = {contact_id: cnt for (contact_id, cnt) in curs.fetchall()}
            print(ret)
            return ret

        def notify_unread(user_id):
            print('notify_unread', user_id)
            if user_id in userid2seeds:
                sio.emit('set_unread_message_count', {'unread_message_count': get_cnt(user_id)},
                         room='set_unread_message_count-' + user_id)

        def new_message_to_user(user_id, message):
            import time
            import datetime
            if not user_id in userid2seeds:
                return False

            contact_id = message['contact_id']
            opened_chatrooms_id_for_reader_user = [sid2userid[sid1][1] for sid1 in
                                                   [sid for sid in userid2seeds[user_id]] if sid2userid[sid1][1]]

            if not contact_id:
                return

            if contact_id in opened_chatrooms_id_for_reader_user:
                print('read-write')
                curs.execute("UPDATE message SET read_tm = clock_timestamp() WHERE id = '%s'" % (message['id'],))

            curs.execute("SELECT user1_id, user2_id FROM contact WHERE contact.id = '%s'" % (contact_id,))
            contact = curs.fetchone()
            for sid in userid2seeds[user_id]:
                tosend = {'id': message['id'],
                          'content': message['content'],
                          'to_user_id': message['to_user_id'],
                          'from_user_id': contact[0 if contact[1] == message['to_user_id'] else 1],
                          'cr_tm': message['cr_tm'],
                          'timestamp': time.mktime(
                              datetime.datetime.strptime(message['cr_tm'], "%Y-%m-%dT%H:%M:%S.%f").timetuple()),
                          }

                sio.emit(event='new_message', data={'chat_room_id': message['contact_id'], 'message': tosend,
                                                    'unread_message_count': get_cnt(user_id)}, room=sid)

        def dblisten():
            from eventlet.hubs import trampoline
            """
            Open a db connection and add notifications to *q*.
            """
            while True:
                trampoline(conn, read=True)
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    print("Got NOTIFY:", notify.pid, notify.channel, notify.payload)
                    (messagetype, message_info_id) = tuple(notify.channel.split('___'))
                    if messagetype == 'new_message_to_user':
                        new_message_to_user(message_info_id.replace('_', '-'), json.loads(notify.payload))
                    elif messagetype == 'message_read_user':
                        notify_unread(message_info_id.replace('_', '-'))

        eventlet.spawn(dblisten)
        app = socketio.Middleware(sio, app)
        eventlet.wsgi.server(eventlet.listen(('', 5000)), app)

        pass
    else:
        from profapp.controllers.blueprints_register import register_profi as register_blueprints_profi
        register_blueprints_profi(app)
        update_jinja_engine(app)

    if apptype in ['profi', 'front']:
        bootstrap.init_app(app)
        mail.init_app(app)

    return app
