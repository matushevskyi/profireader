from .blueprints_declaration import front_bp
from flask import render_template, request, url_for, redirect, g, current_app, session
from ..models.articles import Article, ArticlePortalDivision, ReaderArticlePortalDivision
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
from .request_wrapers import check_right
from ..models.rights import AllowAll
from ..models.elastic import PRElastic
from collections import OrderedDict


def add_tags(articles):
    for article_id in articles:
        articles[article_id]['tags'] = ArticlePortalDivision.get(article_id).get_client_side_dict(fields='tags')[
            'tags']


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
        return g.db().query(PortalDivision).filter_by(portal_id=portal_id,
                                                      portal_division_type_id='index').one()


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
            print(url)
            redirect(url)
    return ''


def get_params(**argv):
    search_text = request.args.get('search_text') or ''
    app = current_app._get_current_object()
    portal = g.db().query(Portal).filter_by(host=request.host).first()
    if portal:
        sub_query = Article.subquery_articles_at_portal(search_text=search_text, portal_id=portal.id)
        return search_text, portal, sub_query
    else:
        return None, None, None


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


# TODO OZ by OZ: portal filter, move portal filtering to decorator

@front_bp.route('details/<string:article_portal_division_id>')
@check_right(AllowAll)
def details(article_portal_division_id):
    search_text, portal, _ = get_params()
    if search_text:
        return redirect(url_for('front.index', search_text=search_text))
    article = ArticlePortalDivision.get(article_portal_division_id)
    article_visibility = article.article_visibility_details()
    article_dict = article.get_client_side_dict(fields='id, title,short, like_count, read_count, cr_tm, '
                                                       'md_tm, visibility,'
                                                       'publishing_tm, keywords, status, long, image_file_id,'
                                                       'division.name, division.portal.id,'
                                                       'company.name|id')
    article_dict['tags'] = [tag.get_client_side_dict() for tag in article.tags]

    division = g.db().query(PortalDivision).filter_by(id=article.portal_division_id).one()
    if article_visibility is not True:
        back_to_url('front.details', host=portal.host, article_portal_division_id=article_portal_division_id)
    else:
        article.add_recently_read_articles_to_session()
    related_articles = g.db().query(ArticlePortalDivision).filter(
        and_(ArticlePortalDivision.id != article.id,
             ArticlePortalDivision.portal_division_id.in_(
                 db(PortalDivision.id).filter(PortalDivision.portal_id == article.division.portal_id))
             )).order_by(ArticlePortalDivision.cr_tm.desc()).limit(5).all()
    favorite = article.check_favorite_status()
    liked = article.check_liked_status()
    liked_count = article.check_liked_count()

    return render_template('front/' + g.portal_layout_path + 'article_details.html',
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           articles_related={
                               a.id: a.get_client_side_dict(fields='id, title, publishing_tm, company.name|id')
                               for a
                               in related_articles},
                           article=article_dict,
                           favorite=favorite,
                           liked=liked,
                           liked_count=liked_count,
                           article_visibility=article_visibility is True,
                           redirect_info=article_visibility
                           )


@front_bp.route('_a/add_delete_favorite/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_favorite(json, article_portal_division_id):
    ReaderArticlePortalDivision.add_delete_favorite_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True}


@front_bp.route('_a/add_delete_liked/<string:article_portal_division_id>/', methods=['OK'])
@check_right(AllowAll)
def add_delete_liked(json, article_portal_division_id):
    article = ArticlePortalDivision.get(article_portal_division_id)
    ReaderArticlePortalDivision.add_delete_liked_user_article(article_portal_division_id, json['on'])
    return {'on': False if json['on'] else True, 'liked_count': article.check_liked_count()}


@front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/')
@front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/<int:page>/')
@check_right(AllowAll)
def subportal_division(division_name, member_company_id, member_company_name, page=1):
    member_company = Company.get(member_company_id)
    search_text, portal, _ = get_params()
    division = get_division_for_subportal(portal.id, member_company_id)
    subportal_division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                                name=division_name).one()
    order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=subportal_division.name, default=10)
    articles, pages, page = Search().search(ArticlePortalDivision().search_filter_default(
        subportal_division.id, company_id=member_company_id), search_text=search_text, page=page,
        order_by=order, pagination=True, items_per_page=items_per_page)

    add_tags(articles)

    # sub_query = Article.subquery_articles_at_portal(
    #     search_text=search_text,
    #     portal_division_id=subportal_division.id). \
    #     filter(db(ArticleCompany,
    #               company_id=member_company_id,
    #               id=ArticlePortalDivision.article_company_id).exists())
    # filter(Company.id == member_company_id)

    # articles, pages, page = pagination(query=sub_query, page=page)

    def url_page_division(page=1, search_text='', **kwargs):
        return url_for('front.subportal_division', division_name=division_name,
                       member_company_id=member_company_id, member_company_name=member_company_name,
                       page=page, search_text=search_text)

    return render_template('front/' + g.portal_layout_path + 'subportal_division.html',
                           articles=articles,
                           subportal=True,
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           current_subportal_division=subportal_division.get_client_side_dict(),
                           member_company=member_company.get_client_side_dict(),
                           pages=pages,
                           page=page,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=search_text,
                           url_page=url_page_division)


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/')
@check_right(AllowAll)
def subportal(member_company_id, member_company_name, page=1):
    search_text, portal, _ = get_params()
    if search_text:
        return redirect(url_for('front.index', search_text=search_text))
    member_company = Company.get(member_company_id)
    division = get_division_for_subportal(portal.id, member_company_id)
    subportal_division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                                portal_division_type_id='index').one()
    return render_template('front/' + g.portal_layout_path + 'subportal.html',
                           subportal=True,
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           current_subportal_division=subportal_division.get_client_side_dict(),
                           member_company=member_company.get_client_side_dict(),
                           current_subportal_division_name='index',
                           pages=False,
                           # current_page=page,
                           # page_buttons=Config.PAGINATION_BUTTONS,
                           # search_text=search_text
                           )


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/address/')
@check_right(AllowAll)
def subportal_address(member_company_id, member_company_name):
    search_text, portal, _ = get_params()

    member_company = Company.get(member_company_id)

    division = get_division_for_subportal(portal.id, member_company_id)

    return render_template('front/' + g.portal_layout_path + 'subportal_address.html',
                           subportal=True,
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           current_subportal_division=False,
                           current_subportal_division_name='address',
                           member_company=member_company.get_client_side_dict(),
                           pages=False,
                           # current_page=page,
                           # page_buttons=Config.PAGINATION_BUTTONS,
                           # search_text=search_text
                           )


@front_bp.route('_c/<string:member_company_id>/<string:member_company_name>/contacts/')
@check_right(AllowAll)
def subportal_contacts(member_company_id, member_company_name):
    search_text, portal, _ = get_params()

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


@front_bp.route('_c/<string:member_company_id>/send_message/', methods=['OK'])
@check_right(AllowAll)
def send_message(json, member_company_id):
    send_to = User.get(json['user_id'])
    send_email(send_to.profireader_email, 'New message',
               'messenger/email_send_message', user_to=send_to, user_from=g.user.get_client_side_dict(),
               in_company=Company.get(member_company_id), message=json['message'])
    return {}


@front_bp.route('/', methods=['GET'])
@front_bp.route('<int:page>/', methods=['GET'])
@check_right(AllowAll)
def index(page=1):
    search_text, portal, _ = get_params()
    if not portal:
        return render_template('front/error.html', message="No portal found %(host)s", dict={'host': request.host})

    division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                      portal_division_type_id='index').one()
    order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
    page = page if session.get('original_search_text') == search_text else 1
    # portal.config.set_division_page_size(page_size_for_divisions={division.name: 1})
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=division.name, default=10)
    articles, pages, page = Search().search(
        ArticlePortalDivision().search_filter_default(division.id),
        # {'class': Company, 'filter': Company.name.ilike('ssssssss')},
        search_text=search_text, page=page, order_by=order, pagination=True,
        items_per_page=items_per_page)

    add_tags(articles)
    session['original_search_text'] = search_text

    return render_template('front/' + g.portal_layout_path + 'division.html',
                           articles=articles,
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           pages=pages,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=search_text)


@front_bp.route('<string:division_name>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
@check_right(AllowAll)
def division(division_name, page=1):
    search_text, portal, _ = get_params()
    division = g.db().query(PortalDivision).filter_by(portal_id=portal.id, name=division_name).one()

    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=division.name, default=10)
    if division.portal_division_type_id == 'catalog' and search_text:
        return redirect(url_for('front.index', search_text=search_text))

    if division.portal_division_type_id == 'news' or division.portal_division_type_id == 'events':

        order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE

        current_division = division.get_client_side_dict()

        es = PRElastic(host='http://elastic.profi:9200')

        articles, pages, page = es.search('articles', 'articles',
                                          filter={"portal_division_id": division.id},
                                          must={("title^100", 'subtitle^50', 'short^10', "long^1",
                                                 'author^50', 'keywords^10'): search_text} if search_text else {},
                                          page=page, items_per_page=items_per_page)

        articles = OrderedDict((a['id'], ArticlePortalDivision.get(a['id']).get_client_side_dict()) for a in articles)

        add_tags(articles)

        def url_page_division(page=1, search_text='', **kwargs):
            return url_for('front.division', division_name=current_division['name'], page=page,
                           search_text=search_text)

        return render_template('front/' + g.portal_layout_path + 'division.html',
                               articles=articles,
                               current_division=current_division,
                               portal=portal_and_settings(portal),
                               pages=pages,
                               url_page=url_page_division,
                               current_page=page,
                               page_buttons=Config.PAGINATION_BUTTONS,
                               search_text=search_text)

    elif division.portal_division_type_id == 'catalog':

        members = {member.id: member.get_client_side_dict(fields="id|company|tags") for
                   member in division.portal.company_members}

        return render_template('front/' + g.portal_layout_path + 'catalog.html',
                               members=members,
                               current_division=division.get_client_side_dict(),
                               portal=portal_and_settings(portal))

    else:
        return 'unknown division.portal_division_type_id = %s' % (division.portal_division_type_id,)
