from flask import Blueprint

from .blueprints_declaration import *

from . import views_index, views_user, views_filemanager, views_article, \
    views_company, views_portal, errors, views_file, views_admin, views_tools, views_tutorial, \
    views_messenger


def register_profi(app):

    # we can not change this url_prefix due to soc-network authentication
    # the following string must be exactly here. why?
    from . import views_auth
    from . import views_tutorial
    from . import views_front


    app.register_blueprint(index_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(filemanager_bp)
    app.register_blueprint(article_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(messenger_bp)
    app.register_blueprint(tutorial_bp)
    app.register_blueprint(front_bp)




def register_front(app):
    from . import views_front
    app.register_blueprint(front_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(company_bp)
    # app.register_blueprint(reader_bp, url_prefix='/')

def register_static(app):
    app.register_blueprint(static_bp)


def register_file(app):
    app.register_blueprint(file_bp)
