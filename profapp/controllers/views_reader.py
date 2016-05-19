from .blueprints_declaration import reader_bp
from flask import render_template, redirect, jsonify, json, request, g, url_for, flash, session
from .request_wrapers import tos_required, check_right
from sqlalchemy import and_
from ..models.pr_base import Search
from ..models.articles import ArticlePortalDivision, ReaderArticlePortalDivision
from ..models.portal import PortalDivision, UserPortalReader, Portal, ReaderUserPortalPlan, ReaderDivision
from .errors import BadDataProvided
from config import Config
from .request_wrapers import ok
from utils.db_utils import db
from flask.ext.login import login_required
import datetime
import time
from ..models.rights import UserIsActive, UserNonBanned


@reader_bp.route('/details_reader/<string:article_portal_division_id>')
@check_right(UserNonBanned)
def details_reader(article_portal_division_id):
    article = ArticlePortalDivision.get(article_portal_division_id)
    article.add_recently_read_articles_to_session()
    article_dict = article.get_client_side_dict(fields='id, title,short, cr_tm, md_tm, '
                                                       'publishing_tm, keywords, status, long, image_file_id,'
                                                       'division.name, division.portal.id,'
                                                       'company.name|id')
    article_dict['tags'] = article.tags
    ReaderArticlePortalDivision.add_to_table_if_not_exists(article_portal_division_id)
    favorite = article.check_favorite_status()

    return render_template('partials/reader/reader_details.html',
                           article=article_dict,
                           favorite=favorite
                           )

@reader_bp.route('/list_reader_from_front/<string:portal_id>', methods=['GET'])
def list_reader_from_front(portal_id):
    portal = Portal.get(portal_id)
    if g.user:
        portals = db(Portal).filter((Portal.id.in_(db(UserPortalReader.portal_id, user_id=g.user.id)))).all()
        if portal in portals:
            return redirect(url_for('reader.list_reader'))
        else:
            return redirect(url_for('reader.reader_subscribe', portal_id=portal_id))
    else:
        return redirect(url_for('general.auth_before_subscribe_to_portal', portal_id=portal_id))


@reader_bp.route('/list_reader', methods=['GET'])
@check_right(UserNonBanned)
def list_reader():
    return render_template('_ruslan/reader/_reader_content.html', favorite=request.args.get('favorite') == 'True')


@reader_bp.route('/list_reader', methods=['OK'])
@check_right(UserNonBanned)
def list_reader_load(json):
    next_page = json.get('next_page') if json.get('next_page') else 1
    search_text = request.args.get('search_text') or ''
    article_fields = 'title|id|subtitle|short|image_file_id|subtitle|publishing_tm|read_count,company.name|logo_file_id|id,' \
                     'division.name,portal.name|host|logo_file_id|id'
    favorite = request.args.get('favorite') == 'True'
    localtime = time.gmtime(time.time())
    filter = and_(ArticlePortalDivision.portal_division_id == db(PortalDivision).filter(
                      PortalDivision.portal_id == db(UserPortalReader, user_id=g.user.id).subquery().c.portal_id).subquery().c.id,
                      ArticlePortalDivision.status == ArticlePortalDivision.STATUSES['PUBLISHED'],
                      ArticlePortalDivision.publishing_tm < datetime.datetime(*localtime[:6])) if not favorite\
            else (ArticlePortalDivision.id == db(ReaderArticlePortalDivision, user_id=g.user.id,
                                        favorite=True).subquery().c.article_portal_division_id)
    articles, pages, page = Search().search({'class': ArticlePortalDivision,
                                             'filter': filter,
                                             'tags': True, 'return_fields': article_fields}, page=1,
                                                items_per_page=5*next_page,
                                                search_text=search_text)
    list_articles = ArticlePortalDivision.get_list_reader_articles(articles)
    return {
        'end': True if pages == 1 or pages == 0 else False,
        'articles': list_articles,
        'pages': pages,
        'current_page': page,
        'page_buttons': Config.PAGINATION_BUTTONS,
        # 'portals': portals,
        'favorite': favorite
    }
# @reader_bp.route('/list_reader')
# @reader_bp.route('/list_reader/<int:page>/')
# @tos_required
# def list_reader(page=1):
#     search_text = request.args.get('search_text') or ''
#     article_fields = 'title|short|image_file_id|subtitle|publishing_tm,company.name|logo_file_id,' \
#                      'division.name,portal.name|host|logo_file_id'
#     favorite = request.args.get('favorite') == 'True'
#     if not favorite:
#         articles, pages, page = Search().search({'class': ArticlePortalDivision,
#                                                  'filter': and_(ArticlePortalDivision.portal_division_id ==
#                                                                 db(PortalDivision).filter(
#                                                                     PortalDivision.portal_id ==
#                                                                     db(UserPortalReader,
#                                                                        user_id=g.user.id).subquery().
#                                                                     c.portal_id).subquery().c.id,
#                                                                 ArticlePortalDivision.status ==
#                                                                 ArticlePortalDivision.STATUSES['PUBLISHED']),
#                                                  'tags': True, 'return_fields': article_fields}, page=page)
#     else:
#         articles, pages, page = Search().search({'class': ArticlePortalDivision,
#                                                  'filter': (ArticlePortalDivision.id == db(ReaderArticlePortalDivision,
#                                                                                            user_id=g.user.id,
#                                                                                            favorite=True).subquery().c.
#                                                             article_portal_division_id),
#                                                  'tags': True, 'return_fields': article_fields}, page=page,
#                                                 search_text=search_text)
#     portals = UserPortalReader.get_portals_for_user() if not articles else None
#     for article_id, article in articles.items():
#         articles[article_id]['company']['logo'] = File().get(articles[article_id]['company']['logo_file_id']).url()
#         articles[article_id]['portal']['logo'] = File().get(articles[article_id]['portal']['logo_file_id']).url()
#         del articles[article_id]['company']['logo_file_id'], articles[article_id]['portal']['logo_file_id']
#     return render_template('partials/reader/reader_base.html',
#                            articles=articles,
#                            pages=pages,
#                            current_page=page,
#                            page_buttons=Config.PAGINATION_BUTTONS,
#                            portals=portals,
#                            favorite=favorite
#                            )


@reader_bp.route('/add_to_favorite/', methods=['OK'])
@check_right(UserNonBanned)
def add_delete_favorite(json):
    return ReaderArticlePortalDivision.add_delete_favorite_user_article(json.get('article')['id'], json.get('article')['is_favorite'])

@reader_bp.route('/add_to_like/', methods=['OK'])
@check_right(UserNonBanned)
def add_delete_like(json):
    ReaderArticlePortalDivision.add_delete_liked_user_article(json.get('article')['id'], json.get('article')['liked'])
    return {'liked':ReaderArticlePortalDivision.count_likes(g.user.id, json.get('article')['id']),
            'list_liked_reader':ReaderArticlePortalDivision.get_list_reader_liked(json.get('article')['id'])}


@reader_bp.route('/subscribe/<string:portal_id>/', methods=['GET'])
@check_right(UserNonBanned)
def reader_subscribe(portal_id):
    user_dict = g.user.get_client_side_dict()
    portal = Portal.get(portal_id)
    if not portal:
        raise BadDataProvided
    user_portal_reader = g.db.query(UserPortalReader).filter_by(user_id=user_dict['id'], portal_id=portal_id).count()
    if not user_portal_reader:
        free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
                               ReaderUserPortalPlan.amount).filter_by(name='free').one()
        start_tm = datetime.datetime.utcnow()
        end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp() + free_plan[1])
        user_portal_reader = UserPortalReader(user_dict['id'], portal_id, status='active', portal_plan_id=free_plan[0],
                                              start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
                                              show_divisions_and_comments=[division_show for division_show in
                                                                           [ReaderDivision(portal_division=division)
                                                                            for division in portal.divisions]])
        g.db.add(user_portal_reader)
        g.db.commit()
        flash('You have successfully subscribed to this portal')
    return redirect(url_for('reader.list_reader'))


@reader_bp.route('/subscribe/', methods=['OK'])
@check_right(UserNonBanned)
def reader_subscribe_registered(json):
    user_dict = g.user.get_client_side_dict()
    portal_id = json['portal_id']
    portal = Portal.get(portal_id)
    if not portal:
        return 'Portal doesn`t exist!'

    user_portal_reader = g.db.query(UserPortalReader).filter_by(user_id=user_dict['id'], portal_id=portal_id).count()

    if not user_portal_reader:
        free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
                               ReaderUserPortalPlan.amount).filter_by(name='free').one()
        start_tm = datetime.datetime.utcnow()
        end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp() + free_plan[1])
        user_portal_reader = UserPortalReader(user_dict['id'], portal_id, status='active', portal_plan_id=free_plan[0],
                                              start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
                                              show_divisions_and_comments=[division_show for division_show in
                                                                           [ReaderDivision(portal_division=division)
                                                                            for division in portal.divisions]])
        g.db.add(user_portal_reader)
        g.db.commit()
        return True
    else:
        return 'You already subscribed on this portal!'



@reader_bp.route('/profile/',  methods=['GET'])
@check_right(UserNonBanned)
def reader_profile():
    return render_template('partials/reader/reader_profile.html')


@reader_bp.route('/profile/', methods=['OK'])
@check_right(UserNonBanned)
def reader_profile_load(json):
    pagination_params = list()
    filter_params = []
    if json.get('paginationOptions'):
        pagination_params.extend([json['paginationOptions']['pageNumber'], json['paginationOptions']['pageSize']])
    if json.get('filter'):
        filter_params = UserPortalReader.get_filter_for_portals_and_plans(
            portal_name=json.get('filter').get('portal_name'), start_end_tm=json.get('filter').get('start_tm'),
            package_name=json.get('filter').get('package_name'))
    portals_and_plans = UserPortalReader.get_portals_and_plan_info_for_user(g.user.id, *pagination_params,
                                                                            filter_params=and_(*filter_params))
    grid_data = []
    for field in portals_and_plans:
        grid_data.append({'user_portal_reader_id': field['id'], 'portal_logo': field['portal_logo'],
                          'portal_name': field['portal_name'], 'package_name': field['plan_name'] + ' - UPGRADE',
                          'start_tm': field['start_tm'], 'end_tm': field['end_tm'], 'article_remains': field['amount'],'id':field['portal_id'],
                          'portal_host': field['portal_host'], 'configure': 'configure'})

    return {'grid_data': grid_data,
            'grid_filters': {'portal_name': [{'value': key['portal_name'], 'label': key['portal_name']}]
                             for key in grid_data}}


@reader_bp.route('/edit_portal_subscription/<string:reader_portal_id>')
@check_right(UserNonBanned)
def edit_portal_subscription(reader_portal_id):
    return render_template('partials/reader/edit_portal_subscription.html')


@reader_bp.route('/edit_portal_subscription/<string:reader_portal_id>', methods=['OK'])
@check_right(UserNonBanned)
def edit_portal_subscription_load(json, reader_portal_id):
    user_portal_reader = db(UserPortalReader, id=reader_portal_id).one()
    if request.args.get('action') == 'load':
        if not user_portal_reader.show_divisions_and_comments:
            user_portal_reader.show_divisions_and_comments = [division_show for division_show in
                                                              [ReaderDivision(portal_division=division)
                                                               for division in user_portal_reader.portal.divisions]]
        divisions = sorted(list(map(lambda div_and_com: {'name': div_and_com.portal_division.name,
                                                         'division_id': div_and_com.division_id,
                                                         'show_divisions_and_comments': list(
                                                             map(lambda args: (args[0], args[1]),
                                                                 div_and_com.show_divisions_and_comments))},
                                    user_portal_reader.show_divisions_and_comments)), key=lambda items: items['name'])
        return {'divisions': divisions, 'reader_portal_id': reader_portal_id}
    return user_portal_reader.validate()


@reader_bp.route('/edit_profile_/<string:reader_portal_id>', methods=['OK'])
@check_right(UserNonBanned)
def edit_profile_submit(json, reader_portal_id):
    divisions_and_comments = db(UserPortalReader, id=reader_portal_id).one().show_divisions_and_comments
    for item in json['divisions']:
        for show_division_and_comments in divisions_and_comments:
            if item['division_id'] == show_division_and_comments.division_id:
                show_division_and_comments.show_divisions_and_comments = item['show_divisions_and_comments']
    return json


@reader_bp.route('/buy_subscription')
@check_right(UserNonBanned)
def buy_subscription():
    return render_template('partials/reader/buy_subscription.html')
