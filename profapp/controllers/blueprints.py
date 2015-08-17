from flask import Blueprint

general_bp = Blueprint('general', __name__)
auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)
article_bp = Blueprint('articles', __name__)
filemanager_bp = Blueprint('filemanager', __name__)
static_bp = Blueprint('static', __name__, static_url_path='')
image_editor_bp = Blueprint('image_editor', __name__)
company_bp = Blueprint('company', __name__)
error_bp = Blueprint('error', __name__)


def register(app):
    from . import views_index
    app.register_blueprint(general_bp, url_prefix='/')

    from . import views_auth
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from . import views_user
    # we can not change this url_prefix due to soc-network authentication
    app.register_blueprint(user_bp, url_prefix='/users')

    from . import views_filemanager
    app.register_blueprint(filemanager_bp, url_prefix='/filemanager')

    app.register_blueprint(static_bp, url_prefix='/static')

    from . import views_article
    app.register_blueprint(article_bp, url_prefix='/articles')

    from . import views_image_editor
    app.register_blueprint(image_editor_bp, url_prefix='/image_editor')

    from . import views_company
    app.register_blueprint(company_bp, url_prefix='/company')

    from . import errors
    app.register_blueprint(error_bp, url_prefix='/error')
