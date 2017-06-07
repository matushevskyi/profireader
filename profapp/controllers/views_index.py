import datetime
import re
import time

from flask import render_template, request, session, redirect, url_for, g
from sqlalchemy import and_, desc

from .blueprints_declaration import index_bp
from .. import utils
from ..controllers import errors
from ..models.materials import Publication, ReaderPublication
from ..models.portal import PortalDivision, UserPortalReader, Portal, ReaderUserPortalPlan, ReaderDivision
from ..models.permissions import UserIsActive, AvailableForAll


@index_bp.route('portals_list/', methods=['GET'], permissions=AvailableForAll())
def portals_list():
    return render_template('general/portals_list.html')


@index_bp.route('portals_list/', methods=['OK'], permissions=AvailableForAll())
def portals_list_load(json):
    filter = (Portal.name.ilike("%" + json['text'] + "%"))
    if g.user:
        filter = and_(filter, ~Portal.id.in_(
            utils.db.query_filter(UserPortalReader.portal_id).filter(UserPortalReader.user_id == g.user.id).all()))

    portals, next_page = Portal.get_page(filter=filter, page=json.get('next_page'), per_page=10)

    return {'list_portals':
                [utils.dict_merge(p.get_client_side_dict(),
                                  {'subscribed': True if UserPortalReader.get_by_portal_id_user_id(portal_id=p.id) else False}) for
                 p in portals],
            'end': True}


@index_bp.route('subscribe/<string:portal_id>', methods=['GET'], permissions=AvailableForAll())
def auth_before_subscribe_to_portal(portal_id):
    session['portal_id'] = portal_id
    return redirect(url_for('auth.login_signup_endpoint', login_signup='login'))


@index_bp.route('list_reader_from_front/<string:portal_id>', methods=['GET'], permissions=AvailableForAll())
def list_reader_from_front(portal_id):
    portal = Portal.get(portal_id)
    if g.user:
        portals = utils.db.query_filter(Portal).filter((Portal.id.in_(utils.db.query_filter(UserPortalReader.portal_id, user_id=g.user.id)))).all()
        if portal in portals:
            return redirect(url_for('index.index'))
        else:
            return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
    else:
        return redirect(url_for('index.auth_before_subscribe_to_portal', portal_id=portal_id))

@index_bp.route('welcome/', methods=['GET'], permissions=AvailableForAll())
def welcome():
    if g.user and g.user.is_authenticated():
        return render_template('general/welcome.html')
    else:
        return redirect(url_for('index.index'))

@index_bp.route('', methods=['GET'], permissions=AvailableForAll())
def index():
    if g.user and g.user.is_authenticated() and getattr(g.user, 'tos', False):
        return render_template('_ruslan/reader/_reader_content.html', favorite=request.args.get('favorite') == 'True')
    return render_template('general/index.html')


@index_bp.route('', methods=['OK'], permissions=UserIsActive())
def list_reader_load(json):
    favorite = request.args.get('favorite') == 'True'
    localtime = time.gmtime(time.time())

    if favorite:
        publication_filter = (
            Publication.id == utils.db.query_filter(ReaderPublication, user_id=g.user.id, favorite=True).subquery().c.publication_id)
    else:
        division_filter = \
            and_(PortalDivision.portal_id == utils.db.query_filter(UserPortalReader, user_id=g.user.id).subquery().c.portal_id)
        publication_filter = and_(
            Publication.portal_division_id == utils.db.query_filter(PortalDivision).filter(division_filter).subquery().c.id,
            Publication.status == Publication.STATUSES['PUBLISHED'],
            Publication.publishing_tm < datetime.datetime(*localtime[:6]))

    publications, next_page = Publication.get_page(filter=publication_filter, order_by=desc(Publication.publishing_tm),
                                                   page=json.get('next_page'), per_page=10)
    return {
        'next_page': next_page,
        'end': next_page < 0,
        'articles': [p.create_article() for p in publications],
        'favorite': favorite
    }


@index_bp.route('add_to_favorite/', methods=['OK'], permissions=UserIsActive())
def add_delete_favorite(json):
    return ReaderPublication.add_delete_favorite_user_article(json.get('article')['id'],
                                                              json.get('article')['is_favorite'])


@index_bp.route('add_to_like/', methods=['OK'], permissions=UserIsActive())
def add_delete_like(json):
    ReaderPublication.add_delete_liked_user_article(json.get('article')['id'], json.get('article')['liked'])
    return {'liked': ReaderPublication.count_likes(g.user.id, json.get('article')['id']),
            'list_liked_reader': ReaderPublication.get_list_reader_liked(json.get('article')['id'])}


@index_bp.route('subscribe/', methods=['OK'], permissions=UserIsActive())
def reader_subscribe_registered(json):
    user_dict = g.user.get_client_side_dict()
    portal_id = json['portal_id']
    portal = Portal.get(portal_id)
    if not portal:
        return 'Portal doesn`t exist!'

    reader_portal = g.db.query(UserPortalReader).filter_by(user_id=user_dict['id'], portal_id=portal_id).count()

    if not reader_portal:
        free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
                               ReaderUserPortalPlan.amount).filter_by(name='free').one()
        start_tm = datetime.datetime.utcnow()
        end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp() + free_plan[1])
        reader_portal = UserPortalReader(user_dict['id'], portal_id, status='active', portal_plan_id=free_plan[0],
                                         start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
                                         show_divisions_and_comments=[division_show for division_show in
                                                                      [ReaderDivision(portal_division=division)
                                                                       for division in portal.divisions]])
        g.db.add(reader_portal)
        g.db.commit()
        return True
    else:
        return 'You already subscribed on this portal!'


@index_bp.route('profile/', methods=['GET'], permissions=UserIsActive())
def reader_profile():
    return render_template('partials/reader/reader_profile.html')


@index_bp.route('profile/', methods=['OK'], permissions=UserIsActive())
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
        grid_data.append({'reader_portal_id': field['id'], 'portal_logo': field['portal_logo'],
                          'portal_name': field['portal_name'], 'package_name': field['plan_name'] + ' - UPGRADE',
                          'start_tm': field['start_tm'], 'end_tm': field['end_tm'], 'article_remains': field['amount'],
                          'id': field['portal_id'],
                          'portal_host': field['portal_host'], 'configure': 'configure'})

    return {'grid_data': grid_data,
            'grid_filters': {'portal_name': [{'value': key['portal_name'], 'label': key['portal_name']}]
                             for key in grid_data}}


@index_bp.route('edit_portal_subscription/<string:reader_portal_id>', permissions=UserIsActive())
def edit_portal_subscription(reader_portal_id):
    return render_template('partials/reader/edit_portal_subscription.html')


@index_bp.route('edit_portal_subscription/<string:reader_portal_id>', methods=['OK'], permissions=UserIsActive())
def edit_portal_subscription_load(json, reader_portal_id):
    reader_portal = utils.db.query_filter(UserPortalReader, id=reader_portal_id).one()
    if request.args.get('action') == 'load':
        if not reader_portal.show_divisions_and_comments:
            reader_portal.show_divisions_and_comments = [division_show for division_show in
                                                         [ReaderDivision(portal_division=division)
                                                          for division in reader_portal.portal.divisions]]
        divisions = sorted(list(map(lambda div_and_com: {'name': div_and_com.portal_division.name,
                                                         'division_id': div_and_com.division_id,
                                                         'show_divisions_and_comments': list(
                                                             map(lambda args: (args[0], args[1]),
                                                                 div_and_com.show_divisions_and_comments))},
                                    reader_portal.show_divisions_and_comments)), key=lambda items: items['name'])
        return {'divisions': divisions, 'reader_portal_id': reader_portal_id}
    return reader_portal.validate()


@index_bp.route('edit_profile_/<string:reader_portal_id>', methods=['OK'], permissions=UserIsActive())
def edit_profile_submit(json, reader_portal_id):
    divisions_and_comments = utils.db.query_filter(UserPortalReader, id=reader_portal_id).one().show_divisions_and_comments
    for item in json['divisions']:
        for show_division_and_comments in divisions_and_comments:
            if item['division_id'] == show_division_and_comments.division_id:
                show_division_and_comments.show_divisions_and_comments = item['show_divisions_and_comments']
    return json


@index_bp.route('buy_subscription', permissions=UserIsActive())
def buy_subscription():
    return render_template('partials/reader/buy_subscription.html')


@index_bp.route('contact_us/', methods=["GET"], permissions=AvailableForAll())
def contact_us():
    return render_template('contact_us.html', data={'email': g.user.address_email if g.user else '', 'message': ''})


@index_bp.route('contact_us/', methods=["OK"], permissions=AvailableForAll())
def contact_us_load(json_data):
    from ..constants import REGEXP
    if not re.match(r'([^\s]{3}[\s]*.*){10}', json_data.get('message', '')):
        return {'error': 'Please write message. at least ten words'}
    elif not re.match(REGEXP.EMAIL, json_data.get('email', '')):
        return {'error': 'Please enter correct email'}
    else:
        utils.email.send_email(subject='Send help message', send_to=["profireader.service@gmail.com"],
                               html=('From ' + json_data['email'] + ': ' + json_data['message']))

        return {}


@index_bp.route('_/add_delete_favorite/<string:publication_id>/', methods=['OK'], permissions=AvailableForAll())
def reader_add_delete_favorite(json, publication_id):
    publication = Publication.get(publication_id).add_delete_favorite(json['on'])
    return {'on': True if json['on'] else False, 'favorite_count': publication.favorite_count()}


@index_bp.route('_/add_delete_liked/<string:publication_id>/', methods=['OK'], permissions=AvailableForAll())
def reader_add_delete_liked(json, publication_id):
    publication = Publication.get(publication_id).add_delete_like(json['on'])
    return {'on': True if json['on'] else False, 'liked_count': publication.liked_count()}
