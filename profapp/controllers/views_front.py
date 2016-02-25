from .blueprints_declaration import front_bp
from flask import render_template, request, url_for, redirect, g, current_app, session
from ..models.articles import Article, ArticlePortalDivision
from ..models.portal import MemberCompanyPortal, PortalDivision, Portal, \
    PortalDivisionSettingsCompanySubportal, PortalConfig
from ..models.company import Company
from utils.db_utils import db
from ..models.users import User
from ..models.company import UserCompany
from ..models.pr_base import Search
from utils.session_utils import back_to_url
from config import Config
from sqlalchemy import and_
from .request_wrapers import ok
from ..utils.pr_email import send_email


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
        return PortalDivisionSettings[0]
    else:
        return g.db().query(PortalDivision).filter_by(portal_id=portal_id,
                                                      portal_division_type_id='index').one()


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


@front_bp.route('/', methods=['GET'])
@front_bp.route('<int:page>/', methods=['GET'])
def index(page=1):
    search_text, portal, _ = get_params()
    portal = None
    if not portal:
        return render_template('front/bird/error.html',
                           message="No portal found {}".format(request.host),
                           )

    division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                      portal_division_type_id='index').one()
    order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
    page = page if session.get('original_search_text') == search_text else 1
    # portal.config.set_division_page_size(page_size_for_divisions={division.name: 1})
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=division.name)
    articles, pages, page = Search().search(
        ArticlePortalDivision().search_filter_default(division.id),
        # {'class': Company, 'filter': Company.name.ilike('ssssssss')},
        search_text=search_text, page=page, order_by=order, pagination=True,
        items_per_page=items_per_page)
    session['original_search_text'] = search_text

    return render_template('front/bird/index.html',
                           articles=articles,
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           pages=pages,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           search_text=search_text)


@front_bp.route('<string:division_name>/', methods=['GET'])
@front_bp.route('<string:division_name>/<int:page>/', methods=['GET'])
def division(division_name, page=1):
    search_text, portal, _ = get_params()
    division = g.db().query(PortalDivision).filter_by(portal_id=portal.id, name=division_name).one()
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=division.name)
    if division.portal_division_type_id == 'catalog' and search_text:
        return redirect(url_for('front.index', search_text=search_text))
    if division.portal_division_type_id == 'news' or division.portal_division_type_id == 'events':
        order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
        articles, pages, page = Search().search(
            ArticlePortalDivision().search_filter_default(division.id),
            search_text=search_text, page=page, order_by=order, pagination=True,
            items_per_page=items_per_page)

        current_division = division.get_client_side_dict()

        def url_page_division(page=1, search_text='', **kwargs):
            return url_for('front.division', division_name=current_division['name'], page=page,
                           search_text=search_text)

        return render_template('front/bird/division.html',
                               articles=articles,
                               current_division=current_division,
                               portal=portal_and_settings(portal),
                               pages=pages,
                               url_page=url_page_division,
                               current_page=page,
                               page_buttons=Config.PAGINATION_BUTTONS,
                               search_text=search_text)

    elif division.portal_division_type_id == 'catalog':

        # sub_query = Article.subquery_articles_at_portal(search_text=search_text,
        # articles, pages, page = pagination(query=sub_query, page=page)

        members = {member.id: member.company.get_client_side_dict() for
                   member in division.portal.company_members}

        return render_template('front/bird/catalog.html',
                               members=members,
                               current_division=division.get_client_side_dict(),
                               portal=portal_and_settings(portal))

    else:
        return 'unknown division.portal_division_type_id = %s' % (division.portal_division_type_id,)


# TODO OZ by OZ: portal filter, move portal filtering to decorator

@front_bp.route('details/<string:article_portal_division_id>')
def details(article_portal_division_id):
    search_text, portal, _ = get_params()
    if search_text:
        return redirect(url_for('front.index', search_text=search_text))
    article = ArticlePortalDivision.get(article_portal_division_id)
    article_visibility = article.article_visibility_details()
    article_dict = article.get_client_side_dict(fields='id, title,short, cr_tm, md_tm, visibility,'
                                                       'publishing_tm, keywords, status, long, image_file_id,'
                                                       'division.name, division.portal.id,'
                                                       'company.name|id')
    article_dict['tags'] = article.tags

    division = g.db().query(PortalDivision).filter_by(id=article.portal_division_id).one()
    if article_visibility is not True:
        back_to_url('front.details', host=portal.host, article_portal_division_id=article_portal_division_id)
        return render_template('front/bird/cant_read_article.html', redirect_info=article_visibility,
                               portal=portal_and_settings(portal),
                               current_division=division.get_client_side_dict())
    related_articles = g.db().query(ArticlePortalDivision).filter(
        and_(ArticlePortalDivision.id != article.id,
             ArticlePortalDivision.portal_division_id.in_(
                 db(PortalDivision.id).filter(PortalDivision.portal_id == article.division.portal_id))
             )).order_by(ArticlePortalDivision.cr_tm.desc()).limit(5).all()
    favorite = False

    return render_template('front/bird/article_details.html',
                           portal=portal_and_settings(portal),
                           current_division=division.get_client_side_dict(),
                           articles_related={
                               a.id: a.get_client_side_dict(fields='id, title, publishing_tm, company.name|id')
                               for a
                               in related_articles},
                           article=article_dict,
                           favorite=favorite
                           )


@front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/')
@front_bp.route('<string:division_name>/_c/<string:member_company_id>/<string:member_company_name>/<int:page>/')
def subportal_division(division_name, member_company_id, member_company_name, page=1):
    member_company = Company.get(member_company_id)
    search_text, portal, _ = get_params()
    division = get_division_for_subportal(portal.id, member_company_id)
    subportal_division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                                name=division_name).one()
    order = Search.ORDER_POSITION if not search_text else Search.ORDER_RELEVANCE
    items_per_page = portal.get_value_from_config(key=PortalConfig.PAGE_SIZE_PER_DIVISION,
                                                  division_name=subportal_division.name)
    articles, pages, page = Search().search(ArticlePortalDivision().search_filter_default(
        subportal_division.id, company_id=member_company_id), search_text=search_text, page=page,
        order_by=order, pagination=True, items_per_page=items_per_page)

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

    return render_template('front/bird/subportal_division.html',
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
def subportal(member_company_id, member_company_name, page=1):
    search_text, portal, _ = get_params()
    if search_text:
        return redirect(url_for('front.index', search_text=search_text))
    member_company = Company.get(member_company_id)
    division = get_division_for_subportal(portal.id, member_company_id)
    subportal_division = g.db().query(PortalDivision).filter_by(portal_id=portal.id,
                                                                portal_division_type_id='index').one()
    return render_template('front/bird/subportal.html',
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
def subportal_address(member_company_id, member_company_name):
    search_text, portal, _ = get_params()

    member_company = Company.get(member_company_id)

    division = get_division_for_subportal(portal.id, member_company_id)

    return render_template('front/bird/subportal_address.html',
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

    return render_template('front/bird/subportal_contacts.html',
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


@front_bp.route('_c/<string:member_company_id>/send_message/', methods=['POST'])
@ok
def send_message(json, member_company_id):
    send_to = User.get(json['user_id'])
    send_email(send_to.profireader_email, 'New message',
               'messanger/email_send_message', user_to=send_to, user_from=g.user_dict,
               in_company=Company.get(member_company_id), message=json['message'])
    return {}
