import os
import secret_data


def database_uri(host, username, password, db_name):
    return 'postgresql+psycopg2://{username}:{password}@{host}/{db_name}'. \
        format(**{'db_name': db_name,
                  'host': host,
                  'username': username,
                  'password': password})


class Config(object):
    # see this:
    # http://flask.pocoo.org/docs/0.10/config/ (SERVER_NAME variable)
    # and this:
    # http://kronosapiens.github.io/blog/2014/08/14/understanding-contexts-in-flask.html
    # we also have to add line
    # 0.0.0.0    profireader.a
    # to /etc/hosts

    # SERVER_NAME = 'profireader.com'
    SITE_TITLE = 'Profireader'

    # Statement for enabling the development environment
    DEBUG = False
    TESTING = False

    MAIL_SERVER = 'smtp.gmail.com:587'
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or \
                    secret_data.MAIL_USERNAME
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or \
                    secret_data.MAIL_PASSWORD
    MAIL_GMAIL = 'profireader.service@gmail.com'
    PROFIREADER_MAIL_SUBJECT_PREFIX = '[Profireader]'
    PROFIREADER_MAIL_SENDER = 'Profireader Admin ' \
                              '<profireader.service@gmail.com>'
    PROFIREADER_ADMIN = os.environ.get('PROFIREADER_ADMIN') or 'Oles'
    PROFIREADER_ADMINS = secret_data.PROFIREADER_ADMINS
    WTF_CSRF_ENABLED = False

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2

# Ratio for image_editor, can be :
# 1.7777777777777777, 1.3333333333333333, 0.6666666666666666, 1
    THUMBNAILS_SIZE = (100, 100)
    IMAGE_EDITOR_RATIO = 1.3333333333333333
    HEIGHT_IMAGE = 300   # px
    ALLOWED_IMAGE_FORMATS = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG',
                             'JPEG2000', 'MSP', 'PCX', 'PNG', 'PPM',
                             'SPIDER', 'TIFF', 'WebP', 'XBM',
                             'XV Thumbnails']

# Pagination
    ITEMS_PER_PAGE = 10
    PAGINATION_BUTTONS = 2

# GOOGLE API
    GOOGLE_API_SECRET_KEY = secret_data.GOOGLE_API_SECRET_KEY
    GOOGLE_API_SECRET_JSON = secret_data.GOOGLE_API_SECRET_JSON
    GOOGLE_API_KEY_SIMPLE = secret_data.GOOGLE_API_KEY_SIMPLE
    YOUTUBE_API = dict(SCOPE="https://www.googleapis.com/auth/youtube",
                       UPLOAD=dict(REDIRECT_URI="http://profireader.com/filemanager/uploader/",
                                   SEND_URI="https://www.googleapis.com/upload/youtube/v3/"
                                            "videos?%s"),
                       CREATE_PLAYLIST=dict(SEND_URI="https://www.googleapis.com/youtube/v3/"
                                                     "playlists?%s"),
                       PLAYLIST_ITEMS=dict(SEND_URI="https://www.googleapis.com/youtube/v3/"
                                                    "playlistItems?%s")
                       )
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

# Base rights will added when user is confirmed in company
    BASE_RIGHT_IN_COMPANY = ['upload_files', 'submit_publications']
    # Define the application directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # UPLOAD_FOLDER = os.path.join(BASE_DIR, 'media')

    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    DATABASE_CONNECT_OPTIONS = {}

    # Enable protection against *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED = False

    # Secret key for wtforms
    WTF_CSRF_ENABLED = False
    WTF_CSRF_SECRET_KEY = secret_data.WTF_CSRF_SECRET_KEY

    host = secret_data.DB_HOST
    username = secret_data.DB_USER
    password = secret_data.DB_PASSWORD
    database = secret_data.DB_NAME

    # Secret key for signing cookies
    SECRET_KEY = secret_data.OAUTH_CONFIG['google']['consumer_secret']

    OAUTH_CONFIG = secret_data.OAUTH_CONFIG

    # PRESERVE_CONTEXT_ON_EXCEPTION = False

    BABEL_DEFAULT_LOCALE = 'uk'
    LANGUAGES = [{'name':'uk', 'display':'Ukrainian'},
                 {'name':'en', 'display':'English'}]



class ProductionDevelopmentConfig(Config):

    #Define database connection parameters
    host = os.getenv('PRODUCTION_SERVER_DB_HOST', Config.host)
    username = os.getenv('PRODUCTION_SERVER_DB_USERNAME', Config.username)
    password = os.getenv('PRODUCTION_SERVER_DB_PASSWORD', Config.password)
    db_name = os.getenv('PRODUCTION_SERVER_DB_NAME', Config.database)

    # SERVER_NAME = os.getenv('PRODUCTION_SERVER_NAME', Config.SERVER_NAME)

    CSRF_ENABLED = False

    # Define production database
    SQLALCHEMY_DATABASE_URI = \
        database_uri(host, username, password, db_name)

    # Use a secure, unique and absolutely secret key for
    # signing the data.
    CSRF_SESSION_KEY = os.getenv('PRODUCTION_SERVER_CSRF_SESSION_KEY', None)

    # Secret key for signing cookies
    SECRET_KEY = os.getenv('PRODUCTION_SERVER_SECRET_KEY', Config.SECRET_KEY)

    SITE_TITLE = os.getenv('PRODUCTION_SERVER_SITE_TITLE', Config.SITE_TITLE)

    # Facebook settings
#    CONSUMER_KEY_FB = os.getenv('PRODUCTION_SERVER_CONSUMER_KEY',
#                                Config.CONSUMER_KEY_FB)
#    CONSUMER_SECRET_FB = os.getenv('PRODUCTION_SERVER_CONSUMER_SECRET',
#                                   Config.CONSUMER_SECRET_FB)


    if 'PRODUCTION_SERVER_DB_HOST' not in os.environ.keys():

        # Statement for enabling the development environment
        DEBUG = True


class FrontConfig(Config):
    # SERVER_NAME = 'companyportal.d.ntaxa.com'
    host = os.getenv('PRODUCTION_SERVER_DB_HOST', 'companyportal.d.ntaxa.com')
    username = os.getenv('PRODUCTION_SERVER_DB_USERNAME', Config.username)
    password = os.getenv('PRODUCTION_SERVER_DB_PASSWORD', Config.password)
    db_name = os.getenv('PRODUCTION_SERVER_DB_NAME', Config.database)

    #SERVER_NAME = os.getenv('PRODUCTION_SERVER_NAME', Config.SERVER_NAME)

    # Define production database
    SQLALCHEMY_DATABASE_URI = \
        database_uri(host, username, password, db_name)

    # Use a secure, unique and absolutely secret key for
    # signing the data.
    CSRF_SESSION_KEY = os.getenv('PRODUCTION_SERVER_CSRF_SESSION_KEY', None)

    # Secret key for signing cookies
    SECRET_KEY = os.getenv('PRODUCTION_SERVER_SECRET_KEY', Config.SECRET_KEY)

    SITE_TITLE = os.getenv('PRODUCTION_SERVER_SITE_TITLE', Config.SITE_TITLE)

    # Facebook settings
#    CONSUMER_KEY_FB = os.getenv('PRODUCTION_SERVER_CONSUMER_KEY',
#                                Config.CONSUMER_KEY_FB)
#    CONSUMER_SECRET_FB = os.getenv('PRODUCTION_SERVER_CONSUMER_SECRET',
#                                   Config.CONSUMER_SECRET_FB)

    if 'PRODUCTION_SERVER_DB_HOST' not in os.environ.keys():

        # Statement for enabling the development environment
        DEBUG = True


class TestingConfig(Config):
    # Statement for enabling the development environment
    DEBUG = True
    TESTING = True

    # Disable protection against *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED = False
    WTF_CSRF_ENABLED = False

    # Define database connection parameters
    host = secret_data.DB_HOST_UNITTEST
    database = secret_data.DB_NAME_UNITTEST

    # Define the database - we are working with
    SQLALCHEMY_DATABASE_URI = \
        database_uri(host, Config.username, Config.password, database)

    SITE_TITLE = "TEST"
