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
    # see also http://flask.pocoo.org/docs/0.10/config/
    # SERVER_NAME variable.
    # we also have to add line
    # 0.0.0.0    profireader.a
    # to /etc/hosts

    #SERVER_NAME = 'aprofi.a.ntaxa.com'
    SERVER_NAME = 'profi.ntaxa.com'
    #SERVER_NAME = 'aprofi.d.ntaxa.com'
    #SERVER_NAME = 'profireader.a:8080'
    #SERVER_NAME = 'profireader.net:8080'

    SITE_TITLE = 'Profireader'

    # Statement for enabling the development environment
    DEBUG = False
    TESTING = False

    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or \
                    secret_data.MAIL_USERNAME
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or \
                    secret_data.MAIL_PASSWORD
    PROFIREADER_MAIL_SUBJECT_PREFIX = '[Profireader]'
    PROFIREADER_MAIL_SENDER = 'Profireader Admin ' \
                              '<profireader.service@gmail.com>'
    PROFIREADER_ADMIN = os.environ.get('PROFIREADER_ADMIN') or 'Oles'
    PROFIREADER_ADMINS = secret_data.PROFIREADER_ADMINS

    # Application threads. A common general assumption is
    # using 2 per available processor cores - to handle
    # incoming requests using one and performing background
    # operations using the other.
    THREADS_PER_PAGE = 2

# Ratio for image_editor, can be :
# 1.7777777777777777, 1.3333333333333333, 0.6666666666666666, 1
    IMAGE_EDITOR_RATIO = 1.3333333333333333
    HEIGHT_IMAGE = 300   # px
    ALLOWED_IMAGE_FORMATS = ['BMP', 'EPS', 'GIF', 'IM', 'JPEG',
                             'JPEG2000', 'MSP', 'PCX', 'PNG', 'PPM',
                             'SPIDER', 'TIFF', 'WebP', 'XBM',
                             'XV Thumbnails']

# Pagination
    ITEMS_PER_PAGE = 5
    PAGINATION_BUTTONS = 4

# GOOGLE API
    GOOGLE_API_SECRET_KEY = secret_data.GOOGLE_API_SECRET_KEY
    GOOGLE_API_SECRET_JSON = secret_data.GOOGLE_API_SECRET_JSON
    YOUTUBE_API = dict(UPLOAD=dict(SCOPE="https://www.googleapis.com/auth/youtube.upload",
                                   REDIRECT_URI="http://profi.ntaxa.com/filemanager/uploader/",
                                   SEND_URI="https://www.googleapis.com/upload/youtube/v3/"
                                            "videos?%s"),
                       CREATE_PLAYLIST=dict(SCOPE="https://www.googleapis.com/auth/youtube",
                                            SEND_URI="https://www.googleapis.com/youtube/v3/playlists?%s")
                       )
    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"
    # MISSING_CLIENT_SECRETS_MESSAGE = """
    # WARNING: Please configure OAuth 2.0
    # To make this sample run you will need to populate the client_secrets.json file
    # found at:%swith information from the Developers Console
    # https://console.developers.google.com/
    # For more information about the client_secrets.json file format, please visit:
    # https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
    # """ % os.path.abspath()

# Base rights will added when user is confirmed in company
    BASE_RIGHT_IN_COMPANY = ['upload_files', 'submit_publications']
    # Define the application directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    # UPLOAD_FOLDER = os.path.join(BASE_DIR, 'media')

    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    DATABASE_CONNECT_OPTIONS = {}

    # Enable protection against *Cross-site Request Forgery (CSRF)*
    CSRF_ENABLED = True

    # Secret key for wtforms
    WTF_CSRF_ENABLED = True
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
#     LANGUAGES = {
#     'en': 'English',
#     'uk': 'Ukrainian'
# }


class ProductionDevelopmentConfig(Config):

    #Define database connection parameters
    host = os.getenv('PRODUCTION_SERVER_DB_HOST', Config.host)
    username = os.getenv('PRODUCTION_SERVER_DB_USERNAME', Config.username)
    password = os.getenv('PRODUCTION_SERVER_DB_PASSWORD', Config.password)
    db_name = os.getenv('PRODUCTION_SERVER_DB_NAME', Config.database)

    SERVER_NAME = os.getenv('PRODUCTION_SERVER_NAME', Config.SERVER_NAME)

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
    SERVER_NAME = 'companyportal.d.ntaxa.com'
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
    host = secret_data.DB_HOST
    database = secret_data.DB_NAME_UNITTEST

    # Define the database - we are working with
    SQLALCHEMY_DATABASE_URI = \
        database_uri(host, Config.username, Config.password, database)

    SITE_TITLE = "TEST"
