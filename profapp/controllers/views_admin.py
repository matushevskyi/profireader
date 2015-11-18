from .blueprints_declaration import admin_bp
from flask import g, request, url_for, render_template, flash, current_app
from .request_wrapers import ok, object_to_dict
from .pagination import pagination
from ..models.translate import TranslateTemplate
from config import Config
from utils.db_utils import db
from sqlalchemy.sql import expression


@admin_bp.route('/translations', methods=['GET'])
def translations():
    return render_template('admin/translations.html')


@admin_bp.route('/translations', methods=['POST'])
@ok
def translations_load(json):
    page = json.get('page') or 1

    params = {}

    subquery = TranslateTemplate.subquery_search(search_text=json.get('search_text') or None,
                                                 template=json.get('template') or None)
    translations, pages, current_page = pagination(subquery, page=page, items_per_page=Config.ITEMS_PER_PAGE)
    tr = [t.get_client_side_dict() for t in translations]
    templates = db(TranslateTemplate.template).group_by(TranslateTemplate.template) \
        .order_by(expression.asc(expression.func.lower(TranslateTemplate.template))).all()
    return {'languages': TranslateTemplate.languages, 'translations': tr,
            'templates': [{'label': t.template, 'value': t.template} for t in templates]}


@admin_bp.route('/translations_save', methods=['POST'])
@ok
def translations_save():
    return {}
