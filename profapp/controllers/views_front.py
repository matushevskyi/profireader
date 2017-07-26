from collections import OrderedDict

from flask import render_template, request, url_for, redirect, g
from sqlalchemy.sql import expression

from config import Config
from .blueprints_declaration import front_bp
from .request_wrapers import get_portal
from .. import utils
from ..models.company import Company
from ..models.elastic import elasticsearch
from ..models.materials import Publication
from ..models.messenger import Socket, Notification
from ..models.portal import MemberCompanyPortal, PortalDivision, Portal, \
    PortalDivisionSettingsCompanySubportal
from ..models.permissions import AvailableForAll
from ..models.users import User
from werkzeug.routing import BaseConverter



def all_tags(portal):
    def url_search_tag_in_index(tag):
        return url_for('front.division', tags=tag, division_name='')

    return {'all': portal.get_client_side_dict(fields='tags')['tags'], 'selected_names': [],
            'url_toggle_tag': url_search_tag_in_index}


def get_search_text_and_division(portal, division_name):
    search_text = request.args.get('search') or ''
    print('division_name', division_name)

    dvsn = g.db().query(PortalDivision).filter_by(portal_id=portal.id)

    if division_name is not None:
        dvsn = dvsn.filter_by(name=division_name)

    # TODO: OZ by OZ: 404 if no company

    return search_text, dvsn.order_by(expression.asc(PortalDivision.position)).first()


def portal_and_settings(portal):
    # TODO OZ by OZ: use polymorphic association and return object here (maybe we even will not need  this function)
    ret = portal.get_client_side_dict(
        more_fields='google_analytics_web_property_id, google_analytics_dimensions, google_analytics_metrics')
    newd = OrderedDict()
    subportals_by_companies_id = OrderedDict()
    for di in ret['divisions']:
        if di['portal_division_type_id'] == PortalDivision.TYPES['company_subportal']:
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
    membership = utils.db.query_filter(MemberCompanyPortal, company_id=member_company.id, portal_id=portal.id).one()
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
    return membership, member_company, di


def elastic_article_to_orm_article(item):
    try:
        ret = Publication.get(item['id']).create_article()
    except:
        raise AssertionError("Can't convert elastic article to orm one. maybe elastic db should be reindexed")

    if '_highlight' in item:
        for k in ['short', 'title', 'subtitle', 'keywords', 'author']:
            if k in item['_highlight']:
                ret[k + '_highlighted'] = '...'.join(item['_highlight'][k])
        if 'short' not in item['_highlight'] and 'long' in item['_highlight']:
            ret['short_highlighted'] = '...' + '...'.join(item['_highlight']['long']) + '...'
    return ret


def elastic_company_to_orm_company(item):
    membership = MemberCompanyPortal.get(item['id'])
    ret = membership.get_client_side_dict(fields="id|company|tags")

    if '_highlight' in item:
        for k, modef_field in {'title': 'name', 'subtitle': 'about', 'short': 'short_description'}.items():
            if k in item['_highlight']:
                ret['company'][modef_field + '_highlighted'] = '...'.join(item['_highlight'][k])
        if 'short' not in item['_highlight'] and 'subtitle' in item['_highlight']:
            ret['company']['short_description_highlighted'] = '...' + '...'.join(item['_highlight']['subtitle']) + '...'
    return ret


def get_tag_elastic_filter(all_tags, tags_selected_by_user):
    wrong_tag_found = False
    elastic_filter = []
    all_tags_text_id = {t['text']: t['id'] for t in all_tags}
    selected_tag_names = []
    if tags_selected_by_user:
        for t in tags_selected_by_user.split('+'):
            if t in all_tags_text_id:
                selected_tag_names.append(t)
                elastic_filter.append({'term': {'tag_ids': all_tags_text_id[t]}})
            else:
                wrong_tag_found = True
    return None if wrong_tag_found else elastic_filter, selected_tag_names


def get_urls_change_tag_page(url_tags, search_text, selected_tag_names):
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

    return url_toggle_tag, url_page_division


def get_search_tags_pages_search(portal, page, tags, search_text):
    items_per_page = 10

    def url_tags(tag_names):
        url_args = {}

        if len(tag_names) > 0:
            url_args['tags'] = '+'.join(tag_names)

        return url_for(request.endpoint, **url_args) + (('?search=' + search_text) if search_text else '')

    afilter = [{'or': [{'term': {'status': 'COMPANY_ACTIVE'}}, {'term': {'status': 'PUBLISHED'}}]},
               {'term': {'portal_id': portal.id}}]

    all_tags = portal.get_client_side_dict(fields='tags')['tags']

    elastic_filter, selected_tag_names = get_tag_elastic_filter(all_tags, tags)

    if elastic_filter is None:
        return dict(redirect=redirect(url_tags(selected_tag_names)))

    afilter += elastic_filter

    search_items, pages, page, messages = elasticsearch.search('front', 'company,article',
                                                               afilter=afilter, page=page,
                                                               items_per_page=items_per_page,
                                                               fields={'title': 100, 'subtitle': 50, 'keywords': 10,
                                                                       'short': 10,
                                                                       'author': 50,
                                                                       'long': {'number_of_fragments': 5}},
                                                               text=search_text)

    def convertelastic_to_model(item):
        if item['_type'] == 'company':
            ret = elastic_company_to_orm_company(item)
        if item['_type'] == 'article':
            ret = elastic_article_to_orm_article(item)
        ret['_type'] = item['_type']
        return ret

    def url_tags(tag_names):
        url_args = {}

        if len(tag_names) > 0:
            url_args['tags'] = '+'.join(tag_names)

        return url_for(request.endpoint, **url_args) + (('?search=' + search_text) if search_text else '')

    url_toggle_tag, url_page_division = get_urls_change_tag_page(url_tags, search_text, selected_tag_names)

    return dict(search_results=[convertelastic_to_model(i) for i in search_items],
                tags={'all': all_tags, 'selected_names': selected_tag_names, 'url_toggle_tag': url_toggle_tag},
                pager={'total': pages, 'current': page,
                       'url_construct': url_page_division,
                       'neighbours': Config.PAGINATION_BUTTONS},
                search={'text': search_text, 'url': url_for('front.search', tags=tags), 'messages': messages})


def get_members_tags_pages_search(portal, dvsn, page, tags, search_text, company_publisher=None):
    items_per_page = 10

    def url_tags(tag_names):
        url_args = {'division_name': dvsn.name}

        if len(tag_names) > 0:
            url_args['tags'] = '+'.join(tag_names)

        return url_for(request.endpoint, **url_args) + (('?search=' + search_text) if search_text else '')

    afilter = [{'term': {'status': MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']}},
               {'term': {'portal_id': portal.id}}]

    all_tags = portal.get_client_side_dict(fields='tags')['tags']

    elastic_filter, selected_tag_names = get_tag_elastic_filter(all_tags, tags)

    if elastic_filter is None:
        return dict(company_members=False, redirect=redirect(url_tags(selected_tag_names)))

    afilter += elastic_filter

    company_members, pages, page, messages = elasticsearch.search('front', 'company',
                                                                  sort=[{"date": "desc"}], afilter=afilter, page=page,
                                                                  items_per_page=items_per_page,
                                                                  fields={'title': 100, 'subtitle': 50, 'keywords': 10,
                                                                          'short': 10,
                                                                          'author': 50,
                                                                          'long': {'number_of_fragments': 5}},
                                                                  text=search_text)

    url_toggle_tag, url_page_division = get_urls_change_tag_page(url_tags, search_text, selected_tag_names)

    return dict(memberships=OrderedDict((membership.id, membership.get_client_side_dict(fields="id|company|tags"))
                                        for membership in [MemberCompanyPortal.get(m['id']) for m in company_members]),
                tags={'all': all_tags, 'selected_names': selected_tag_names,
                      'url_toggle_tag': url_toggle_tag},
                pager={'total': pages, 'current': page, 'neighbours': Config.PAGINATION_BUTTONS,
                       'url_construct': url_page_division},
                search={'text': search_text, 'url': url_for('front.search')})


def get_articles_tags_pages_search(portal, dvsn, page, tags, search_text, company_publisher=None):
    items_per_page = 10

    pdt = dvsn.portal_division_type_id

    def url_tags(tag_names):
        url_args = {}

        if pdt != 'index':
            url_args['division_name'] = dvsn.name
        if len(tag_names) > 0:
            url_args['tags'] = '+'.join(tag_names)

        return url_for(request.endpoint, **url_args) + (('?search=' + search_text) if search_text else '')

    afilter = [{'term': {'status': Publication.STATUSES['PUBLISHED']}},
               {'range': {"date": {"lt": "now"}}},
               {'term': {'portal_id': portal.id} if pdt == 'index' else {'division_id': dvsn.id}}]

    if company_publisher:
        afilter.append({'term': {'company_id': company_publisher.id}})

    all_tags = portal.get_client_side_dict(fields='tags')['tags']

    elastic_filter, selected_tag_names = get_tag_elastic_filter(all_tags, tags)

    if elastic_filter is None:
        return dict(articles=False, redirect=redirect(url_tags(selected_tag_names)))

    afilter += elastic_filter

    publications, pages, page, messages = elasticsearch.search('front', 'article',
                                                               sort=[{"date": "desc"}], afilter=afilter, page=page,
                                                               items_per_page=items_per_page,
                                                               fields={'title': 100, 'subtitle': 50, 'keywords': 10,
                                                                       'short': 10,
                                                                       'author': 50,
                                                                       'long': {'number_of_fragments': 5}},
                                                               text=search_text)

    url_toggle_tag, url_page_division = get_urls_change_tag_page(url_tags, search_text, selected_tag_names)

    return dict(articles=OrderedDict((p['id'], elastic_article_to_orm_article(p)) for p in publications),
                tags={'all': all_tags, 'selected_names': selected_tag_names, 'url_toggle_tag': url_toggle_tag},
                pager={'total': pages, 'current': page, 'neighbours': Config.PAGINATION_BUTTONS,
                       'url_construct': url_page_division},
                search={'text': search_text, 'url': url_for('front.search')})


subportal_prefix = '_c/<string:member_company_id>/<string:member_company_name>/'


def url_catalog_toggle_tag(portal, tag_text):
    catalog_division = utils.db.query_filter(PortalDivision, portal_id=portal.id,
                                             portal_division_type_id=PortalDivision.TYPES['catalog']).one()
    return url_for('front.division', division_name=catalog_division.name, tags=tag_text)


@front_bp.route(subportal_prefix, permissions=AvailableForAll())
@front_bp.route(subportal_prefix + '<string:member_company_page>/', permissions=AvailableForAll())
@get_portal
def company_page(portal, member_company_id, member_company_name, member_company_page='about'):
    if member_company_page not in ['about', 'address', 'contacts']:
        member_company_page = 'about'
    # TODO: OZ by OZ: redirect if company name is wrong. 404 if id is wrong
    membership, member_company, dvsn = \
        get_company_member_and_division(portal, member_company_id, member_company_name)


    return render_template('front/' + g.portal_layout_path + 'company_' + member_company_page + '.html',
                           portal=portal_and_settings(portal),
                           division=dvsn.get_client_side_dict(),
                           seo=membership.seo_dict(),
                           analytics=portal.get_analytics(page_type='company_subportal', company_id=member_company_id),
                           tags=all_tags(portal),
                           membership=membership,
                           url_catalog_tag=lambda tag_text: url_catalog_toggle_tag(portal, tag_text),
                           member_company=member_company.get_client_side_dict(
                               more_fields='employments,employments.user,employments.user.avatar.url'),
                           company_menu_selected_item=member_company_page,
                           member_company_page=member_company_page)


@front_bp.route('/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<int:page>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('tags/<string:tags>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<int:page>/tags/<string:tags>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<transliterate:division_name>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<transliterate:division_name>/<int:page>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<transliterate:division_name>/tags/<string:tags>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<transliterate:division_name>/<int:page>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('<transliterate:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route(subportal_prefix + '_d/<transliterate:division_name>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route(subportal_prefix + '_d/<transliterate:division_name>/<int:page>/', methods=['GET'],
                permissions=AvailableForAll())
@front_bp.route(subportal_prefix + '_d/<transliterate:division_name>/tags/<string:tags>/', methods=['GET'],
                permissions=AvailableForAll())
@front_bp.route(subportal_prefix + '_d/<transliterate:division_name>/<int:page>/tags/<string:tags>/', methods=['GET'],
                permissions=AvailableForAll())
@get_portal
def division(portal, division_name=None, page=1, tags=None, member_company_id=None, member_company_name=None):
    # this function was created to work with search in division also. I just commented this feature in case we will want back it
    # functions get_members_tags_pages_search and get_articles_tags_pages_search still works (should work) with search text but we pass there None
    if member_company_id is None:

        search_text, dvsn = get_search_text_and_division(portal, division_name)

        if dvsn.portal_division_type_id in ['index', 'news', 'events']:

            articles_data = get_articles_tags_pages_search(portal, dvsn, page, tags, None)
            if 'redirect' in articles_data:
                return articles_data['redirect']

            return render_template(
                'front/' + g.portal_layout_path + 'division_articles.html',
                division=dvsn.get_client_side_dict(),
                seo=dvsn.seo_dict(),
                analytics=portal.get_analytics(page_type=dvsn.portal_division_type_id),
                portal=portal_and_settings(portal),
                **articles_data)

        elif dvsn.portal_division_type_id == 'catalog':

            membership_data = get_members_tags_pages_search(portal, dvsn, page, tags, None)

            return render_template('front/' + g.portal_layout_path + 'division_catalog.html',
                                   division=dvsn.get_client_side_dict(),
                                   portal=portal_and_settings(portal),
                                   seo=dvsn.seo_dict(),
                                   analytics=portal.get_analytics(page_type=dvsn.portal_division_type_id),
                                   **membership_data
                                   )
        elif dvsn.portal_division_type_id == 'company_subportal':
            member_company_page = 'about'

            membership, member_company, dvsn = \
                get_company_member_and_division(portal, dvsn.settings['company_id'], member_company_name)

            return render_template('front/' + g.portal_layout_path + 'company_' + member_company_page + '.html',
                                   portal=portal_and_settings(portal),
                                   division=dvsn.get_client_side_dict(),
                                   tags=all_tags(portal),
                                   seo=membership.seo_dict(),
                                   analytics=portal.get_analytics(page_type=dvsn.portal_division_type_id,
                                                             company_id=member_company.id),
                                   membership=utils.db.query_filter(MemberCompanyPortal, company_id=member_company.id,
                                                                    portal_id=portal.id).one(),
                                   url_catalog_tag=lambda tag_text: url_catalog_toggle_tag(portal, tag_text),
                                   member_company=member_company.get_client_side_dict(
                                       more_fields='employments,employments.user,employments.user.avatar.url'),
                                   company_menu_selected_item=member_company_page,
                                   member_company_page=member_company_page)
        else:
            return 'unknown division.portal_division_type_id = %s' % (dvsn.portal_division_type_id,)

    else:

        # TODO: OZ by OZ: redirect if company name is wrong. 404 if id is wrong
        membership, member_company, dvsn = \
            get_company_member_and_division(portal, member_company_id, member_company_name)
        search_text, subportal_dvsn = get_search_text_and_division(portal, division_name)

        articles_data = get_articles_tags_pages_search(portal, subportal_dvsn, page, tags, None,
                                                       company_publisher=member_company)
        if 'redirect' in articles_data:
            return articles_data['redirect']

        return render_template('front/' + g.portal_layout_path + 'division_company.html',
                               portal=portal_and_settings(portal),
                               division=dvsn.get_client_side_dict(),
                               seo=membership.seo_dict(),
                               analytics=portal.get_analytics(page_type=dvsn.portal_division_type_id,
                                                         company_id=member_company.id),
                               member_company=member_company.get_client_side_dict(),
                               membership=membership.get_client_side_dict(fields="id|company|tags"),
                               url_catalog_tag=lambda tag_text: url_catalog_toggle_tag(portal, tag_text),
                               company_menu_selected_item=subportal_dvsn.get_client_side_dict(),
                               **articles_data
                               )


@front_bp.route('_a/<string:publication_id>/<transliterate:publication_title>', permissions=AvailableForAll())
@get_portal
def article_details(portal, publication_id, publication_title):
    # TODO: OZ by OZ: redirect if title is wrong
    publication = Publication.get(publication_id)
    article_visibility = publication.article_visibility_details()

    division = g.db().query(PortalDivision).filter_by(id=publication.portal_division_id).one()
    if article_visibility is True:
        publication.add_to_read()
    else:
        utils.session.back_to_url('front.article_details', host=portal.host, publication_id=publication_id,
                                  publication_title=publication_title)

    def url_search_tag(tag):
        return url_for('front.division', tags=tag, division_name=division.name)

    return render_template('front/' + g.portal_layout_path + 'article_details.html',
                           portal=portal_and_settings(portal),
                           tags=all_tags(portal),
                           division=division.get_client_side_dict(),
                           seo=publication.seo_dict(),
                           analytics=portal.get_analytics(page_type='publication',
                                                     company_id=publication.material.company_id,
                                                     publication_visibility=publication.visibility,
                                                     publication_reached='True' if article_visibility is True else 'False'),
                           article=publication.create_article(),
                           article_visibility=article_visibility,
                           articles_related=publication.get_related_articles(),
                           )


@front_bp.route('_s/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('_s/<int:page>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('_s/tags/<string:tags>/', methods=['GET'], permissions=AvailableForAll())
@front_bp.route('_s/tags/<string:tags>/<int:page>/', methods=['GET'], permissions=AvailableForAll())
@get_portal
def search(portal, page=1, tags=None):
    search_data = get_search_tags_pages_search(portal, page, tags, request.args.get('search') or '')

    return render_template('front/' + g.portal_layout_path + 'search.html',
                           seo={'title': '', 'description': '', 'keywords': ''},
                           analytics=portal.get_analytics(page_type='other'),
                           portal=portal_and_settings(portal), **search_data)


@front_bp.route('_/add_delete_favorite/<string:publication_id>/', methods=['OK'], permissions=AvailableForAll())
def add_delete_favorite(json, publication_id):
    publication = Publication.get(publication_id).add_delete_favorite(json['on'])
    return {'on': True if json['on'] else False, 'favorite_count': publication.favorite_count()}


@front_bp.route('_/add_delete_liked/<string:publication_id>/', methods=['OK'], permissions=AvailableForAll())
def add_delete_liked(json, publication_id):
    publication = Publication.get(publication_id).add_delete_like(json['on'])
    return {'on': True if json['on'] else False, 'liked_count': publication.liked_count()}


@front_bp.route('_/<string:member_company_id>/send_message/', methods=['OK'], permissions=AvailableForAll())
@get_portal
def send_message(portal, json, member_company_id):
    send_to = User.get(json['user_id'])
    company = Company.get(member_company_id)
    send_to.NOTIFY_MESSAGE_FROM_PORTAL_FRONT(message=json['message'], portal=portal, company=company)
    return {}


@front_bp.route('robots.txt', methods=['GET'], strict_slashes=True, permissions=AvailableForAll())
def robots_txt():
    return "User-agent: *\n"


@front_bp.route('sitemap.xml', methods=['GET'], strict_slashes=True, permissions=AvailableForAll())
@get_portal
def sitemap(portal):
    from sqlalchemy import desc

    return render_template('front/sitemap.xml', portal=portal,
                           divisions=[{
                                          'loc': portal.host + url_for('front.division',
                                                                       division_name=d.name),
                                          'lastmod': max(d.md_tm, (g.db().query(Publication).filter_by(
                                              portal_division_id=d.id).order_by(
                                              desc(Publication.md_tm)).first() or d).md_tm)
                                      } for d in portal.divisions],
                           companies=[{
                                          'loc': url_for('front.company_page', member_company_name=m.company.name,
                                                         member_company_id=m.company.id),
                                          'lastmod': m.company.md_tm
                                      } for m in portal.company_memberships if
                                      m.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']],
                           articles=[{
                                         'loc': url_for('front.article_details', publication_id=p.id,
                                                        publication_title=p.material.title),
                                         'lastmod': p.md_tm
                                     } for p in portal.publications if p.status == Publication.STATUSES['PUBLISHED']]
                           )


@get_portal
def error_404(portal):
    return render_template('front/' + g.portal_layout_path + '404.html',
                           seo={'title': '', 'description': '', 'keywords': ''},
                           analytics=portal.get_analytics(page_type='other'),
                           tags=all_tags(g.portal),
                           portal=portal_and_settings(g.portal))


