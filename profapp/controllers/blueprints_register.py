from flask import Blueprint

# general_bp = Blueprint('general', __name__)
# auth_bp = Blueprint('auth', __name__)
# user_bp = Blueprint('user', __name__)
# article_bp = Blueprint('article', __name__)
# filemanager_bp = Blueprint('filemanager', __name__)
# static_bp = Blueprint('static', __name__, static_url_path='')
# image_editor_bp = Blueprint('image_editor', __name__)
# company_bp = Blueprint('company', __name__)
# portal_bp = Blueprint('portal', __name__)
# front_bp = Blueprint('front', __name__)
# file_bp = Blueprint('file', __name__)
# exception_bp = Blueprint('exception', __name__)
# help_bp = Blueprint('help', __name__)

from .blueprints_declaration import *
from . import views_index, views_user, views_filemanager, views_article, \
    views_company, views_portal, errors, views_file, views_admin, views_tools, views_help, views_reader, views_tutorial, \
    views_messanger


def register_profi(app):

    # we can not change this url_prefix due to soc-network authentication
    # the following string must be exactly here. why?
    from . import views_auth
    from . import views_tutorial

    app.register_blueprint(general_bp, url_prefix='/')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tools_bp, url_prefix='/tools')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(filemanager_bp, url_prefix='/filemanager')
    app.register_blueprint(article_bp, url_prefix='/articles')
    app.register_blueprint(image_editor_bp, url_prefix='/image_editor')
    app.register_blueprint(company_bp, url_prefix='/company')
    app.register_blueprint(portal_bp, url_prefix='/portal')
    app.register_blueprint(exception_bp, url_prefix='/exception')
    app.register_blueprint(help_bp, url_prefix='/help')
    app.register_blueprint(messenger_bp, url_prefix='/messenger')
    app.register_blueprint(tutorial_bp, url_prefix='/tutorial')


    from . import views_front

    app.register_blueprint(reader_bp, url_prefix='/reader')

    app.register_blueprint(front_bp, url_prefix='/')

    # app.register_blueprint(reader_bp, url_prefix='/')


def register_front(app):
    from . import views_front
    app.register_blueprint(front_bp, url_prefix='/')
    app.register_blueprint(user_bp, url_prefix='/users')
    # app.register_blueprint(reader_bp, url_prefix='/')

def register_static(app):
    app.register_blueprint(static_bp)


def register_file(app):
    app.register_blueprint(file_bp, url_prefix='/')
