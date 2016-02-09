from .blueprints_declaration import reader_bp
from flask import render_template, redirect, jsonify, json, request, g, url_for, flash
from .request_wrapers import tos_required
from sqlalchemy import and_
from ..models.articles import ArticlePortalDivision, ReaderArticlePortalDivision, Search
from ..models.portal import PortalDivision, UserPortalReader, Portal, ReaderUserPortalPlan, ReaderDivision
from .errors import BadDataProvided
from config import Config
from .request_wrapers import ok
from utils.db_utils import db
import datetime
from ..models.files import File


@reader_bp.route('/details_reader/<string:article_portal_division_id>')
@tos_required
def details_reader(article_portal_division_id):
    article = ArticlePortalDivision.get(article_portal_division_id)
    article.add_recently_read_articles_to_session()
    article_dict = article.get_client_side_dict(fields='id, title,short, cr_tm, md_tm, '
                                                       'publishing_tm, keywords, status, long, image_file_id,'
                                                       'division.name, division.portal.id,'
                                                       'company.name|id')
    article_dict['tags'] = article.tags
    ReaderArticlePortalDivision.add_to_table_if_not_exists(article_portal_division_id)
    favorite = article.check_favorite_status(user_id=g.user.id)

    return render_template('partials/reader/reader_details.html',
                           article=article_dict,
                           favorite=favorite
                           )


@reader_bp.route('/list_reader')
@reader_bp.route('/list_reader/<int:page>/')
@tos_required
def list_reader(page=1):

    search_text = request.args.get('search_text') or ''
    article_fields = 'title|short|subtitle|publishing_tm,company.name|logo_file_id,' \
                     'division.name,portal.name|host|logo_file_id'
    favorite = request.args.get('favorite') == 'True'
    if not favorite:
        articles, pages, page = Search.search({'class': ArticlePortalDivision,
                                               'filter': and_(ArticlePortalDivision.portal_division_id ==
                                                              db(PortalDivision).filter(
                                                                  PortalDivision.portal_id ==
                                                                  db(UserPortalReader, user_id=g.user.id).subquery().
                                                                  c.portal_id).subquery().c.id,
                                                              ArticlePortalDivision.status ==
                                                              ArticlePortalDivision.STATUSES['PUBLISHED']),
                                               'tags': True, 'return_fields': article_fields}, page=page)
    else:
        articles, pages, page = Search.search({'class': ArticlePortalDivision,
                                               'filter': (ArticlePortalDivision.id == db(ReaderArticlePortalDivision,
                                                                                         user_id=g.user.id,
                                                                                         favorite=True).subquery().c.
                                                          article_portal_division_id),
                                               'tags': True, 'return_fields': article_fields}, page=page,
                                              search_text=search_text)
    portals = UserPortalReader.get_portals_for_user() if not articles else None
    for article_id, article in articles.items():
        articles[article_id]['company']['logo'] = File().get(articles[article_id]['company']['logo_file_id']).url()
        articles[article_id]['portal']['logo'] = File().get(articles[article_id]['portal']['logo_file_id']).url()
        del articles[article_id]['company']['logo_file_id'], articles[article_id]['portal']['logo_file_id']

    return render_template('partials/reader/reader_base.html',
                           articles=articles,
                           pages=pages,
                           current_page=page,
                           page_buttons=Config.PAGINATION_BUTTONS,
                           portals=portals,
                           favorite=favorite
                           )


@reader_bp.route('add_to_favorite/', methods=['POST'])
def add_delete_favorite():
    favorite = json.loads(request.form.get('favorite'))
    article_portal_division_id = request.form.get('article_portal_division_id')
    ReaderArticlePortalDivision.add_delete_favorite_user_article(article_portal_division_id, favorite)
    return jsonify({'favorite': favorite})


@reader_bp.route('/subscribe/<string:portal_id>')
@tos_required
def reader_subscribe(portal_id):
    user_dict = g.user_dict
    portal = Portal.get(portal_id)
    if not portal:
        raise BadDataProvided

    user_portal_reader = g.db.query(UserPortalReader).filter_by(user_id=user_dict['id'], portal_id=portal_id).count()
    if not user_portal_reader:
        free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
                               ReaderUserPortalPlan.amount).filter_by(name='free').one()
        start_tm = datetime.datetime.utcnow()
        end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp()+free_plan[1])
        user_portal_reader = UserPortalReader(user_dict['id'], portal_id, status='active', portal_plan_id=free_plan[0],
                                              start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
                                              show_divisions_and_comments=[division_comments for division_comments in
                                                                           [ReaderDivision(portal_division=division)
                                                                            for division in portal.divisions]])
        g.db.add(user_portal_reader)
        g.db.commit()

        flash('You have successfully subscribed to this portal')

    return redirect(url_for('reader.list_reader'))


@reader_bp.route('/profile/')
def profile():
    return render_template('partials/reader/reader_profile.html')


@reader_bp.route('/profile/', methods=['POST'])
@ok
def profile_load(json):
    pagination_params = list()
    filter_params = []
    if json.get('paginationOptions'):
        pagination_params.extend([json['paginationOptions']['pageNumber'], json['paginationOptions']['pageSize']])
    if json.get('filter'):
        if json.get('filter').get('portal_name'):
            filter_params.append(UserPortalReader.portal_id.in_(db(Portal.id).filter(
                Portal.name.ilike('%' + json.get('filter').get('portal_name') + '%'))))
        if json.get('filter').get('start_tm'):
            from_tm = datetime.datetime.utcfromtimestamp(int(json.get('filter').get('start_tm')['from'] + 1) / 1000)
            to_tm = datetime.datetime.utcfromtimestamp(int(json.get('filter').get('start_tm')['to'] + 86399999) / 1000)
            filter_params.extend([UserPortalReader.start_tm >= from_tm,
                                  UserPortalReader.start_tm <= to_tm])
    portals_and_plans = UserPortalReader.get_portals_and_plan_info_for_user(g.user.id, *pagination_params,
                                                                            filter_params=and_(*filter_params))
    grid_data = []
    for field in portals_and_plans:
        grid_data.append({'user_portal_reader_id': field['id'], 'portal_logo': field['portal_logo'],
                          'portal_name': field['portal_name'], 'package_name': field['plan_name'] + ' - UPGRADE',
                          'start_tm': field['start_tm'], 'end_tm': field['end_tm'], 'article_remains': field['amount'],
                          'portal_host': field['portal_host'], 'configure': 'configure'})

    return {'grid_data': grid_data,
            'grid_filters': {'portal_name': [{'value': key['portal_name'], 'label': key['portal_name']}]
                             for key in grid_data}}


@reader_bp.route('/edit_portal_subscription/<string:reader_portal_id>')
def edit_portal_subscription(reader_portal_id):

    return render_template('partials/reader/edit_portal_subscription.html')


@reader_bp.route('/edit_portal_subscription/<string:reader_portal_id>', methods=['POST'])
@ok
def edit_portal_subscription_load(json, reader_portal_id):
    user_portal_reader = db(UserPortalReader, id=reader_portal_id).one()
    divisions = list(map(lambda div_and_com: {'name': div_and_com.portal_division.name,
                                              'division_id': div_and_com.division_id,
                                              'show_divisions_and_comments': list(
                                                  map(lambda args: (args[0], args[1]),
                                                      div_and_com.show_divisions_and_comments))},
                         user_portal_reader.show_divisions_and_comments))
    return {'divisions': divisions, 'reader_portal_id': reader_portal_id}


@reader_bp.route('/edit_profile_submit/<string:reader_portal_id>', methods=['POST'])
@ok
def edit_profile_submit(json, reader_portal_id):
    divisions_and_comments = db(UserPortalReader, id=reader_portal_id).one().show_divisions_and_comments
    for item in json['divisions']:
        for show_division_and_comments in divisions_and_comments:
            if item['division_id'] == show_division_and_comments.division_id:
                show_division_and_comments.show_divisions_and_comments = item['show_divisions_and_comments']
    return json