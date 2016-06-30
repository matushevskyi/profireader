from .blueprints_declaration import front_bp
from flask import render_template, request, url_for, redirect, g, current_app, session
# from ..models.bak_articles import Article, Publication, ReaderPublication
from ..models.materials import Publication, ReaderPublication, Material
from ..models.portal import MemberCompanyPortal, PortalDivision, Portal, \
    PortalDivisionSettingsCompanySubportal, PortalConfig, UserPortalReader
from ..models.company import Company
from utils.db_utils import db
from ..models.users import User
from ..models.company import UserCompany
from ..models.pr_base import Search
from utils.session_utils import back_to_url
from config import Config
from sqlalchemy import and_
from ..utils.pr_email import send_email
from .request_wrapers import check_right, get_portal
from ..models.rights import AllowAll
from ..models.elastic import elasticsearch
from collections import OrderedDict
from .. import utils


def get_division_for_subportal(portal_id, member_company_id):
    q = g.db().query(PortalDivisionSettingsCompanySubportal). \
        join(MemberCompanyPortal,
             MemberCompanyPortal.id == PortalDivisionSettingsCompanySubportal.member_company_portal_id). \
        join(PortalDivision,
             PortalDivision.id == PortalDivisionSettingsCompanySubportal.portal_division_id). \
        filter(MemberCompanyPortal.company_id == member_company_id). \
        filter(PortalDivision.portal_id == portal_id)
    PortalDivisionSettings = q.all()
    if (len(PortalDivisionSettings)):
        return PortalDivisionSettings[0].portal_division
    else:
        return g.db().query(PortalDivision).filter_by(portal_id=portal_id, portal_division_type_id='catalog').one()


@front_bp.route('subscribe_to_portal/')
@check_right(AllowAll)
def subscribe_to_portal():
    portal = g.db().query(Portal).filter_by(host=request.host).first()
    if g.user:
        portals = UserPortalReader.get_portals_for_user()
        if portal in portals:
            redirect(url_for('reader.list_reader'))
        else:
            url = '//profireader.com/subscribe/' + portal.id
            redirect(url)
    return ''


def get_search_text_and_division(portal, division_name):
    search_text = request.args.get('search') or ''

    dvsn = g.db().query(PortalDivision).filter_by(**utils.dict_merge(
        {'portal_id': portal.id},
        {'portal_division_type_id': 'index'} if division_name is None else {'name': division_name})).one()

    return search_text, dvsn


def portal_and_settings(portal):
    ret = portal.get_client_side_dict()
    newd = []
    for di in ret['divisions']:
        if di['portal_division_type_id'] == 'company_subportal':
            pdset = g.db().query(PortalDivisionSettingsCompanySubportal). \
                filter_by(portal_division_id=di['id']).first()
            com_port = g.db().query(MemberCompanyPortal).get(pdset.member_company_portal_id)
            di['member_company'] = Company.get(com_port.company_id)
        newd.append(di)
    ret['divisions'] = newd
    ret['advs'] = {a.place: a.html for a in portal.advs}
    return ret


# @front_bp.route('favicon.ico')
# def favicon():
#     return send_from_directory(os.path.join(current_app.root_path, 'static'),
#                                'favicon.ico', mimetype='image/vnd.microsoft.icon')



@front_bp.route('_a/add_delete_favorite/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_favorite(json, article_portal_division_id):
    ReaderPublication.add_delete_favorite_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True}


@front_bp.route('_a/add_delete_liked/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_liked(json, article_portal_division_id):
    article = Publication.get(article_portal_division_id)
    ReaderPublication.add_delete_liked_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True, 'liked_count': article.check_liked_count()}


# @front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/')
# @front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/<int:page>/')
# @check_right(AllowAll)
# def subportal_division(division_name, member_company_id, member_company_name, page=1):
#     member_company = Company.get(member_company_id)
#     search_text, portal, _ = get_params()
#     division = get_division_for_subportal(portal.id, member_company_id)
#     subportal_division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
#                                                                 name=division_name).one()
#     order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
#     items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
#                                                   division_name=subportal_division.name, default=10)
#     articles, pages, page = Search().search(Publication().search_filter_default(
#         subportal_division.id, company_id=member_company_id), search_text=search_text, page=page,
#         order_by=order, pagination=True, items_per_page=items_per_page)
#
#     add_tags(articles)
#
#     # sub_query = Article.subquery_articles_at_portal(
#     #     search_text=search_text,
#     #     portal_division_id=subportal_division.id). \
#     #     filter(db(ArticleCompany,
#     #               company_id=member_company_id,
#     #               id=Publication.article_company_id).exists())
#     # filter(Company.id == member_company_id)
#
#     # articles, pages, page = pagination(query=sub_query, page=page)
#
#     def url_page_division(page=1, search_text='', **kwargs):
#         return url_for('front.subportal_division', division_name=division_name,
#                        member_company_id=member_company_id, member_company_name=member_company_name,
#                        page=page, search_text=search_text)
#
#     return render_template('front/' + g.portal_layout_path + 'bak_subportal_division.html',
#                            articles=articles,
#                            subportal=True,
#                            portal=portal_and_settings(portal),
#                            current_division=division.get_client_side_dict(),
#                            current_subportal_division=subportal_division.get_client_side_dict(),
#                            member_company=member_company.get_client_side_dict(),
#                            pages=pages,
#                            page=page,
#                            current_page=page,
#                            page_buttons=Config.PAGINATION_BUTTONS,
#                            search_text=search_text,
#                            url_page=url_page_division)


@front_bp.route('_c/<string:member_company_id>/send_message/', methods=['OK'])
@check_right(AllowAll)
def send_message(json, member_company_id):
    send_to = User.get(json['user_id'])
    send_email(send_to.profireader_email, 'New message',
               'messenger/email_send_message', user_to=send_to, user_from=g.user.get_client_side_dict(),
               in_company=Company.get(member_company_id), message=json['message'])
    return {}


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/address/')
@check_right(AllowAll)
@get_portal
def subportal_address(portal, member_company_id, member_company_name):
    # TODO: OZ by OZ
    _, dvsn = get_search_text_and_division(portal, 'index')
    subportal_for_company = Company.get(member_company_id)

    division = get_division_for_subportal(portal.id, member_company_id)

    return render_template('front/' + g.portal_layout_path + 'subportal_address.html',
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           member_company=subportal_for_company.get_client_side_dict(),
                           member_company_page='address',
                           )


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/address/')
@check_right(AllowAll)
@get_portal
def company_member(portal, member_company_id, member_company_name):
    #TODO: OZ by OZ
    _, dvsn = get_search_text_and_division(portal, 'index')
    subportal_for_company = Company.get(member_company_id)

    division = get_division_for_subportal(portal.id, member_company_id)

    return render_template('front/' + g.portal_layout_path + 'subportal_address.html',
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           member_company=subportal_for_company.get_client_side_dict(),
                           member_company_page='address',
                           )


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/contacts/')
@check_right(AllowAll)
@get_portal
def subportal_contacts(portal, member_company_id, member_company_name):
    # TODO: OZ by OZ
    search_text, portal = get_search_text_and_division(portal, 'index')

    member_company = Company.get(member_company_id)

    division = get_division_for_subportal(portal.id, member_company_id)

    company_users = member_company.employees

    # TODO: AA by OZ: remove this. llok also for ERROR employees.position.2
    # ERROR employees.position.2#
    def getposition(u_id, c_id):
        r = db(UserCompany, user_id=u_id, company_id=c_id).first()
        return r.position if r else ''

    return render_template('front/' + g.portal_layout_path + 'subportal_contacts.html',
                           subportal=True,
                           company_users={
                               u.id: dict(u.get_client_side_dict(), position=getposition(u.id, member_company_id)) for u
                               in
                               company_users},
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           current_subportal_division=False,
                           current_subportal_division_name='contacts',
                           member_company=member_company.get_client_side_dict(),
                           pages=False,
                           # current_page=page,
                           # page_buttons=Config.PAGINATION_BUTTONS,
                           # search_text=search_text
                           )


def publication_id_to_article(p_id):
    p = Publication.get(p_id)
    return utils.dict_merge(
        p.get_client_side_dict(),
        Material.get(p.material_id).get_client_side_dict(fields='long|short|title|subtitle|keywords|illustration')
    )


def render_articles(portal, dvsn, page, tags, search_text):
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=dvsn.name, default=10)

    pdt = dvsn.portal_division_type_id

    current_division = dvsn.get_client_side_dict()

    def url_tags(tag_names):
        url_args = {}

        if pdt != 'index':
            url_args['division_name'] = current_division['name']
        if len(tag_names) > 0:
            url_args['tags'] = '+'.join(tag_names)

        s = ('?search=' + search_text) if search_text else ''

        return url_for(request.endpoint, **url_args) + s

    def url_page_division(page=1):
        s = ('?search=' + search_text) if search_text else ''
        url_args = utils.dict_merge(request.view_args, {'page': page} if page > 1 else {},
                                    remove={} if page > 1 else {'page': True})
        return url_for(request.endpoint, **url_args) + s

    def url_toggle_tag(toggle_tag):
        new_tags = utils.list_merge(selected_tag_names,
                                    [toggle_tag] if (toggle_tag and toggle_tag not in selected_tag_names) else [],
                                    remove=[toggle_tag] if toggle_tag and toggle_tag in selected_tag_names else [])

        return url_tags(new_tags)

    afilter = [] if pdt == 'index' else [{'term': {'portal_division_id': dvsn.id}}]
    wrong_tag = False
    all_tags = (portal.get_client_side_dict(fields='tags') if pdt == 'index' else current_division)['tags']
    all_tags_text_id = {t['text']: t['id'] for t in all_tags}
    selected_tag_names = []
    if tags:
        for t in tags.split('+'):
            if t in all_tags_text_id:
                selected_tag_names.append(t)
                afilter.append({'term': {'tag_ids': all_tags_text_id[t]}})
            else:
                wrong_tag = True

    if wrong_tag:
        return redirect(url_tags(selected_tag_names))
        # url_for(request.endpoint,
        #                     **utils.dict_merge(request.view_args, {'tags': '+'.join(selected_tag_names)})))

    publications, pages, page = elasticsearch.search('publications', 'publications',
                                                     sort=[{"date": "desc"}], filter=afilter, page=page,
                                                     items_per_page=items_per_page,
                                                     must=[{"multi_match": {'query': search_text,
                                                                            'fields': ["title^100", 'subtitle^50',
                                                                                       'short^10',
                                                                                       "long^1",
                                                                                       'author^50',
                                                                                       'keywords^10']}}] if search_text else [])


    return render_template('front/' + g.portal_layout_path + 'division.html',
                           articles=OrderedDict((p['id'], publication_id_to_article(p['id'])) for p in publications),
                           current_division=current_division,
                           all_tags=all_tags,
                           selected_tag_names=selected_tag_names,
                           portal=portal_and_settings(portal),
                           pages=pages,
                           url_page=url_page_division,
                           url_toggle_tag=url_toggle_tag,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=search_text)


# subportal_prefix = '<string:subportal_division_name>/'

@front_bp.route('/', methods=['GET'])
@front_bp.route('<int:page>/', methods=['GET'])
@front_bp.route('tags/<string:tags>/', methods=['GET'])
@front_bp.route('<int:page>/tags/<string:tags>/', methods=['GET'])
@front_bp.route('<string:division_name>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route('<string:division_name>/tags/<string:tags>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'])
# @front_bp.route(subportal_prefix)
# @front_bp.route(subportal_prefix + '<int:page>/')
# @front_bp.route(subportal_prefix + '<int:page>/tags/<string:tags>/', methods=['GET'])
# @front_bp.route(subportal_prefix + '<string:division_name>/', methods=['GET'])
# @front_bp.route(subportal_prefix + '<string:division_name>/<int:page>/', methods=['GET'])
# @front_bp.route(subportal_prefix + '<string:division_name>/tags/<string:tags>/', methods=['GET'])
# @front_bp.route(subportal_prefix + '<string:division_name>/<int:page>/', methods=['GET'])
# @front_bp.route(subportal_prefix + '<string:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'])
@check_right(AllowAll)
@get_portal
def division(portal, division_name=None, page=1, tags=None, member_company_name=None, member_company_id=None):
    search_text, dvsn = get_search_text_and_division(portal, division_name)

    if dvsn.portal_division_type_id == 'catalog' and search_text:
        return redirect(url_for('front.index', search_text=search_text))

    if dvsn.portal_division_type_id == 'company_subportal':
        member_company = MemberCompanyPortal.get(g.db().query(PortalDivisionSettingsCompanySubportal).filter_by(
            portal_division_id=dvsn.id).one().member_company_portal_id)
        return render_template('front/' + g.portal_layout_path + 'subportal_about.html',
                               portal=portal_and_settings(portal),
                               current_division=dvsn.get_client_side_dict(),
                               member_company=member_company.get_client_side_dict(),
                               member_company_division=dvsn.get_client_side_dict(),
                               member_company_page='about',
                               )

    if dvsn.portal_division_type_id in ['index', 'news', 'events']:
        return render_articles(portal, dvsn, page, tags, search_text)

    elif dvsn.portal_division_type_id == 'catalog':
        members = {member.id: member.get_client_side_dict(fields="id|company|tags") for
                   member in dvsn.portal.company_members}
        return render_template('front/' + g.portal_layout_path + 'catalog.html',
                               members=members,
                               current_division=dvsn.get_client_side_dict(),
                               portal=portal_and_settings(portal))

    else:
        return 'unknown division.portal_division_type_id = %s' % (dvsn.portal_division_type_id,)


@front_bp.route('details/<string:publication_id>')
@check_right(AllowAll)
@get_portal
def details(portal, publication_id):
    publication = Publication.get(publication_id)
    article_visibility = publication.article_visibility_details()
    article_dict = publication_id_to_article(publication.id)


    division = g.db().query(PortalDivision).filter_by(id=publication.portal_division_id).one()
    if article_visibility is not True:
        back_to_url('front.details', host=portal.host, publication_id=publication_id)
    else:
        publication.add_recently_read_articles_to_session()
    related_articles = g.db().query(Publication).filter(
        and_(Publication.id != publication.id,
             Publication.portal_division_id.in_(
                 db(PortalDivision.id).filter(PortalDivision.portal_id == publication.division.portal_id))
             )).order_by(Publication.cr_tm.desc()).limit(5).all()
    favorite = publication.check_favorite_status()
    liked = publication.check_liked_status()
    liked_count = publication.check_liked_count()

    def url_toggle_tag(toggle_tag):
        return url_for('front.division', tags=toggle_tag)

    return render_template('front/' + g.portal_layout_path + 'article_details.html',
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           articles_related={
                               # TODO: OZ by OZ: restore it
                               # a.id: a.get_client_side_dict(fields='id, title, publishing_tm, company.name|id')
                               # for a
                               # in related_articles
                               },
                           article=article_dict,
                           favorite=favorite,
                           url_toggle_tag=url_toggle_tag,
                           liked=liked,
                           liked_count=liked_count,
                           article_visibility=article_visibility is True,
                           redirect_info=article_visibility,
                           )
