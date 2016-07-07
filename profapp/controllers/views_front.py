from .blueprints_declaration import front_bp
from flask import render_template, request, url_for, redirect, g
from ..models.materials import Publication, ReaderPublication, Material
from ..models.portal import MemberCompanyPortal, PortalDivision, Portal, \
    PortalDivisionSettingsCompanySubportal, PortalConfig, UserPortalReader
from ..models.company import Company
from ..models.users import User
from utils.session_utils import back_to_url
from config import Config
from ..utils.pr_email import send_email
from .request_wrapers import check_right, get_portal
from ..models.rights import AllowAll
from ..models.elastic import elasticsearch
from collections import OrderedDict
from .. import utils


def get_search_text_and_division(portal, division_name):
    search_text = request.args.get('search') or ''

    dvsn = g.db().query(PortalDivision).filter_by(**utils.dict_merge(
        {'portal_id': portal.id},
        {'portal_division_type_id': 'index'} if division_name is None else {'name': division_name})).one()

    # TODO: OZ by OZ: 404 if no company

    return search_text, dvsn


def portal_and_settings(portal):
    # TODO OZ by OZ: use polymorphic association and return object here (maybe we even will not need  this function)
    ret = portal.get_client_side_dict()
    newd = OrderedDict()
    subportals_by_companies_id = OrderedDict()
    for di in ret['divisions']:
        if di['portal_division_type_id'] == 'company_subportal':
            pdset = g.db().query(PortalDivisionSettingsCompanySubportal). \
                filter_by(portal_division_id=di['id']).first()
            com_port = g.db().query(MemberCompanyPortal).get(pdset.member_company_portal_id)
            di['subportal_company'] = Company.get(com_port.company_id)
            subportals_by_companies_id[com_port.company_id] = di
        newd[di['id']] = di
    ret['divisions'] = newd
    ret['subportals_by_companies_id'] = subportals_by_companies_id
    ret['advs'] = {a.place: a.html for a in portal.advs}
    return ret


def get_company_member_and_division(portal: Portal, company_id, company_name):
    # TODO: OZ by OZ: redirect if name is wrong
    portal_dict = portal_and_settings(portal)
    # TODO: OZ by OZ: heck company is member
    member_company = Company.get(company_id)
    di = None
    for d_id, d in portal_dict['divisions'].items():
        if 'subportal_company' in d and d['subportal_company'].id == company_id:
            di = g.db().query(PortalDivisionSettingsCompanySubportal). \
                join(MemberCompanyPortal,
                     MemberCompanyPortal.id == PortalDivisionSettingsCompanySubportal.member_company_portal_id). \
                join(PortalDivision,
                     PortalDivision.id == PortalDivisionSettingsCompanySubportal.portal_division_id). \
                filter(MemberCompanyPortal.company_id == member_company.id). \
                filter(PortalDivision.portal_id == portal.id).one().portal_division

    if not di:
        # TODO: YG: by OZ: change all hardcoded portal_division_types_id (like '<here some index>') to PortalDivision.TYPES[<here some index>]
        di = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                    portal_division_type_id=PortalDivision.TYPES[
                                                        'catalog']).first()
    if not di:
        di = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                    portal_division_type_id=PortalDivision.TYPES[
                                                        'index']).one()
    return member_company, di


def publication_id_to_article(p_id):
    p = Publication.get(p_id)
    return utils.dict_merge(
        p.get_client_side_dict(),
        Material.get(p.material_id).get_client_side_dict(fields='long|short|title|subtitle|keywords|illustration')
    )


def get_articles_tags_pages_search_text(portal, dvsn, page, tags, search_text, company_publisher=None):
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=dvsn.name, default=200)

    pdt = dvsn.portal_division_type_id

    def url_tags(tag_names):
        url_args = {}

        if pdt != 'index':
            url_args['division_name'] = dvsn.name
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

    afilter = [
        {'term': {'status': Publication.STATUSES['PUBLISHED']}},
        {'term': {'portal_id': portal.id}}] if pdt == 'index' else [{'term': {'portal_division_id': dvsn.id}}]

    if company_publisher:
        afilter.append({'term': {'publisher_company_id': company_publisher.id}})

    wrong_tag = False
    all_tags = (portal.get_client_side_dict(fields='tags') if pdt == 'index' else dvsn.get_client_side_dict(
        fields='tags'))['tags']
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

    return dict(articles=OrderedDict((p['id'], publication_id_to_article(p['id'])) for p in publications),
                tags={'all': all_tags, 'selected_names': selected_tag_names, 'url_construct_toggle': url_toggle_tag},
                pager={'total': pages, 'current': page, 'neighbours': Config.PAGINATION_BUTTONS,
                       'url_construct': url_page_division},
                search_text=search_text)


subportal_prefix = '_c/<string:member_company_id>/<string:member_company_name>/'


@front_bp.route(subportal_prefix)
@front_bp.route(subportal_prefix + '<string:member_company_page>/')
@check_right(AllowAll)
@get_portal
def company_page(portal, member_company_id, member_company_name, member_company_page='about'):
    # TODO: OZ by OZ: redirect if company name is wrong. 404 if id is wrong
    member_company, dvsn = \
        get_company_member_and_division(portal, member_company_id, member_company_name)

    return render_template('front/' + g.portal_layout_path + 'company_' + member_company_page + '.html',
                           portal=portal_and_settings(portal),
                           division=dvsn.get_client_side_dict(),
                           member_company=member_company.get_client_side_dict(
                               more_fields='employments,employments.user'),
                           company_menu_selected_item=member_company_page,
                           member_company_page=member_company_page,
                           )


@front_bp.route('/', methods=['GET'])
@front_bp.route('<int:page>/', methods=['GET'])
@front_bp.route('tags/<string:tags>/', methods=['GET'])
@front_bp.route('<int:page>/tags/<string:tags>/', methods=['GET'])
@front_bp.route('<string:division_name>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route('<string:division_name>/tags/<string:tags>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'])
@front_bp.route(subportal_prefix + '_d/<string:division_name>/', methods=['GET'])
@front_bp.route(subportal_prefix + '_d/<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route(subportal_prefix + '_d/<string:division_name>/tags/<string:tags>/', methods=['GET'])
@front_bp.route(subportal_prefix + '_d/<string:division_name>/<int:page>/', methods=['GET'])
@front_bp.route(subportal_prefix + '_d/<string:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'])
@check_right(AllowAll)
@get_portal
def division(portal, division_name=None, page=1, tags=None, member_company_id=None, member_company_name=None):
    if member_company_id is None:
        search_text, dvsn = get_search_text_and_division(portal, division_name)

        if dvsn.portal_division_type_id in ['index', 'news', 'events']:
            return render_template(
                'front/' + g.portal_layout_path + 'division_articles.html',
                division=dvsn.get_client_side_dict(),
                portal=portal_and_settings(portal),
                **get_articles_tags_pages_search_text(portal, dvsn, page, tags, search_text))

        elif dvsn.portal_division_type_id == 'catalog':
            members = {member.id: member.get_client_side_dict(fields="id|company|tags") for
                       member in dvsn.portal.company_members}
            return render_template('front/' + g.portal_layout_path + 'division_catalog.html',
                                   members=members,
                                   division=dvsn.get_client_side_dict(),
                                   portal=portal_and_settings(portal))

        else:
            return 'unknown division.portal_division_type_id = %s' % (dvsn.portal_division_type_id,)

    else:
        # TODO: OZ by OZ: redirect if company name is wrong. 404 if id is wrong
        member_company, dvsn = \
            get_company_member_and_division(portal, member_company_id, member_company_name)
        search_text, subportal_dvsn = get_search_text_and_division(portal, division_name)

        return render_template('front/' + g.portal_layout_path + 'division_company.html',
                               portal=portal_and_settings(portal),
                               division=dvsn.get_client_side_dict(),
                               member_company=member_company.get_client_side_dict(),
                               company_menu_selected_item=subportal_dvsn.get_client_side_dict(),
                               **get_articles_tags_pages_search_text(portal, subportal_dvsn, page, tags, search_text,
                                                                     company_publisher=member_company)
                               )


@front_bp.route('_a/<string:publication_id>/<string:publication_title>')
@check_right(AllowAll)
@get_portal
def article_details(portal, publication_id, publication_title):
    # TODO: OZ by OZ: redirect if title is wrong
    publication = Publication.get(publication_id)
    articles_related = publication.get_related_articles()
    article_visibility = publication.article_visibility_details()
    article_dict = publication_id_to_article(publication.id)

    division = g.db().query(PortalDivision).filter_by(id=publication.portal_division_id).one()
    if article_visibility is True:
        publication.add_recently_read_articles_to_session()
    else:
        back_to_url('front.article_details', host=portal.host, publication_id=publication_id)

    def url_toggle_tag(toggle_tag):
        return url_for('front.division', tags=toggle_tag)

    return render_template('front/' + g.portal_layout_path + 'article_details.html',
                           portal=portal_and_settings(portal),
                           division=division.get_client_side_dict(),
                           article=article_dict,
                           article_visibility=article_visibility,
                           articles_related=articles_related,
                           tags={'all': [], 'selected_names': [],
                                 'url_construct_toggle': url_toggle_tag},
                           article_social_activity={
                               'favorite': publication.check_favorite_status(),
                               'liked': publication.check_liked_status(),
                               'liked_count': publication.check_liked_count()
                           },
                           url_toggle_tag=url_toggle_tag,
                           )


@front_bp.route('_/add_delete_favorite/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_favorite(json, article_portal_division_id):
    ReaderPublication.add_delete_favorite_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True}


@front_bp.route('_/add_delete_liked/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_liked(json, article_portal_division_id):
    article = Publication.get(article_portal_division_id)
    ReaderPublication.add_delete_liked_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True, 'liked_count': article.check_liked_count()}


@front_bp.route('_/<string:member_company_id>/send_message/', methods=['OK'])
@check_right(AllowAll)
def send_message(json, member_company_id):
    send_to = User.get(json['user_id'])
    send_email(send_to.profireader_email, 'New message',
               'messenger/email_send_message', user_to=send_to,
               user_from=g.user.get_client_side_dict() if g.user else None,
               in_company=Company.get(member_company_id), message=json['message'])
    return {}
