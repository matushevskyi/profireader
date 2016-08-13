from .blueprints_declaration import admin_bp
from flask import g, request, url_for, render_template, flash, current_app
from .request_wrapers import ok
from .pagination import pagination
from .request_wrapers import check_right
from flask.ext.login import login_required
from ..models.translate import TranslateTemplate
from ..models.ip import Ips
from utils.db_utils import db
from sqlalchemy.sql import expression
import datetime
from ..models.config import Config
from flask import session
from ..models.pr_base import Grid
from ..models.rights import UserIsActive

@admin_bp.route('/translations', methods=['GET'])
@check_right(UserIsActive)
def translations():
    return render_template('admin/translations.html',
                           angular_ui_bootstrap_version='//angular-ui.github.io/bootstrap/ui-bootstrap-tpls-0.14.2.js')

# class test:
#     a = 1
#
#     def __init__(self, n):
#         self.a = n
#
# @admin_bp.route('/set_session_a', methods=['OK'])
# @check_right(UserIsActive)
# def set_session_a(json):
#     z = session['test'] if 'test' in session else None
#     # print(z.a)
#     y = test('a')
#     session['test'] = y
#     return {'old_value': z.__repr__(), 'new_value': session['test'].__repr__()}
#
# @admin_bp.route('/set_session_b', methods=['OK'])
# @check_right(UserIsActive)
# def set_session_b(json):
#     z = session['test'] if 'test' in session else None
#     # print(z.a)
#     y = test('b')
#     session['test'] = y
#     return {'old_value': z.__repr__(), 'new_value': session['test'].__repr__()}

@admin_bp.route('/translations', methods=['OK'])
@check_right(UserIsActive)
def translations_load(json):
    subquery = TranslateTemplate.subquery_search(json.get('filter'), json.get('sort') , json.get('editItem'))

    translations, pages, current_page, count = pagination(subquery, **Grid.page_options(json.get('paginationOptions')))

    grid_filters = {
        'template': [{'value': portal[0], 'label': portal[0]} for portal in
                    db(TranslateTemplate.template).group_by(TranslateTemplate.template) \
        .order_by(expression.asc(expression.func.lower(TranslateTemplate.template))).all()],
        'url': [{'value': portal[0], 'label': portal[0]} for portal in
                    db(TranslateTemplate.url).group_by(TranslateTemplate.url) \
        .order_by(expression.asc(expression.func.lower(TranslateTemplate.url))).all()]
    }
    return {'grid_data': [translation.get_client_side_dict() for translation in translations],
            'grid_filters': {k: [{'value': None, 'label': TranslateTemplate.getTranslate('', '__-- all --')}] + v for
                             (k, v) in grid_filters.items()},
            'total': count
            }


@admin_bp.route('/translations_save', methods=['OK'])
@check_right(UserIsActive)
def translations_save(json):
    exist = db(TranslateTemplate, template=json['row'], name=json['col']).first()
    return TranslateTemplate.get(exist.id).attr({json['lang']: json['val']}).save().get_client_side_dict()

@admin_bp.route('/delete', methods=['OK'])
@check_right(UserIsActive)
def delete_translates(json):
    return TranslateTemplate.delete_translates(json['objects'])

# Greckas ips

@admin_bp.route('/ips', methods=['GET'])
@check_right(UserIsActive)
def ips():
    return render_template('admin/ips.html',
                           angular_ui_bootstrap_version='//angular-ui.github.io/bootstrap/ui-bootstrap-tpls-0.14.2.js')

@admin_bp.route('/ips', methods=['OK'])
@check_right(UserIsActive)
def ips_load(json):
    page = json.get('paginationOptions')['pageNumber']
    pageSize = json.get('paginationOptions')['pageSize']
    params = {}
    params['sort'] = {}
    params['filter'] = {}
    params['search_text'] = {}

    if json.get('sort'):
        for n in json.get('sort'):
            params['sort'][n] = json.get('sort')[n]
    if json.get('filter'):
        for b in json.get('filter'):
            if json.get('filter')[b] != '-- all --':
                params['filter'][b] = json.get('filter')[b]
    if json.get('search_text'):
        for d in json.get('search_text'):
            params['search_text'][d] = json.get('search_text')[d]
    if json.get('editItem'):
        exist = db(Ips, template=json.get('editItem')['template'], name=json.get('editItem')['name']).first()
        i = datetime.datetime.now()
        Ips.get(exist.id).attr({json.get('editItem')['col']: json.get('editItem')['newValue'], 'md_tm':i}).save().get_client_side_dict()
    subquery = Ips.subquery_search(**params)

    translations, pages, current_page, count = pagination(subquery, page=page, items_per_page=pageSize)
    add_param = {'value': '1','label': '-- all --'}

    templates = db(TranslateTemplate.template).group_by(TranslateTemplate.template) \
        .order_by(expression.asc(expression.func.lower(TranslateTemplate.template))).all()
    urls = db(TranslateTemplate.url).group_by(TranslateTemplate.url) \
        .order_by(expression.asc(expression.func.lower(TranslateTemplate.url))).all()

    urls_g = TranslateTemplate.list_for_grid_tables(urls, add_param,False)
    templates_g = TranslateTemplate.list_for_grid_tables(templates, add_param,False)
    grid_data = TranslateTemplate.getListGridDataTranslation(translations)
    grid_filters = {'template': templates_g,'url': urls_g}

    return {'grid_data': grid_data,
            'grid_filters': grid_filters,
            'total': subquery.count()
            }

@admin_bp.route('/ips_save', methods=['OK'])
@check_right(UserIsActive)
def ips_save(json):
    exist = db(Ips, template=json['row'], name=json['col']).first()
    return Ips.get(exist.id).attr({json['lang']: json['val']}).save().get_client_side_dict()


@admin_bp.route('/ips_add', methods=['OK'])
@check_right(UserIsActive)
def ips_add(json):

     exist = db(Ips, template=json['row'], name=json['col']).first()
     return Ips.get(exist.id).attr({json['lang']: json['val']}).add().get_client_side_dict()

@admin_bp.route('/ips_delete', methods=['OK'])
@check_right(UserIsActive)
def ips_delete(json):
    return Ips.delete(json['objects'])



# Greckas config


@admin_bp.route('/config', methods=['GET'])
@check_right(UserIsActive)
def config():
    return render_template('admin/config.html',
                           angular_ui_bootstrap_version='//angular-ui.github.io/bootstrap/ui-bootstrap-tpls-0.14.2.js')


@admin_bp.route('/config', methods=['OK'])
@check_right(UserIsActive)
def config_load(json):
    page = json.get('paginationOptions')['pageNumber']
    pageSize = json.get('paginationOptions')['pageSize']
    params = {}
    params['sort'] = {}
    params['filter'] = {}
    params['search_text'] = {}
    if json.get('sort'):
        for n in json.get('sort'):
            params['sort'][n] = json.get('sort')[n]
    if json.get('filter'):
        for b in json.get('filter'):
            if json.get('filter')[b] != '-- all --':
                params['filter'][b] = json.get('filter')[b]
    if json.get('search_text'):
        for d in json.get('search_text'):
            params['search_text'][d] = json.get('search_text')[d]
    if json.get('editItem'):
        exist = db(Config, template=json.get('editItem')['template'], name=json.get('editItem')['name']).first()
        i = datetime.datetime.now()
        Config.get(exist.id).attr({json.get('editItem')['col']: json.get('editItem')['newValue'], 'md_tm':i}).save().get_client_side_dict()
    subquery = Config.subquery_search(template=json.get('template') or None,
                                                 url=json.get('url') or None,
                                                 **params)

    translations, pages, current_page, count = pagination(subquery, page=page, items_per_page=pageSize)
    grid_data = TranslateTemplate.getListGridDataTranslation(translations)

    return {'grid_data': grid_data,
            'total': subquery.count()
            }


