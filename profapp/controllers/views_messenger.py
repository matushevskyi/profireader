from flask import render_template, g
from sqlalchemy import and_, or_
from sqlalchemy.sql import expression

from .blueprints_declaration import messenger_bp
from .errors import BadDataProvided
from .request_wrapers import check_right
from ..models.company import Company, UserCompany
from ..models.messenger import Contact
from ..models.portal import Portal, UserPortalReader
from ..models.rights import UserIsActive
from ..models.users import User


@messenger_bp.route('/', methods=['GET'])
@check_right(UserIsActive)
def messenger():
    return render_template('messenger/messenger.html')


@messenger_bp.route('/', methods=['OK'])
@check_right(UserIsActive)
def messenger_load(json):
    return {}


@messenger_bp.route('/community_search/', methods=['OK'])
@check_right(UserIsActive)
def community_search(json):
    PER_PAGE = 20
    portals_ids = []
    for p in g.user.active_portals_subscribed:
        portals_ids.append(p.id)

    companies_ids = []
    for c in g.user.active_companies_employers:
        companies_ids.append(c.id)

    # use load_for_infinite_scroll
    # TODO: OZ by OZ: use load_for_infinite_scroll

    query = g.db.query(User). \
        outerjoin(UserPortalReader,
                  and_(UserPortalReader.user_id == User.id, UserPortalReader.status == 'active',
                       UserPortalReader.portal_id.in_(portals_ids))). \
        outerjoin(Portal,
                  and_(UserPortalReader.portal_id == Portal.id, Portal.status == 'ACTIVE')). \
        outerjoin(UserCompany,
                  and_(UserCompany.user_id == User.id, UserCompany.status == 'ACTIVE',
                       UserCompany.company_id.in_(companies_ids))). \
        outerjoin(Company,
                  and_(UserCompany.company_id == Company.id, Company.status == 'ACTIVE')). \
        outerjoin(Contact,
                  or_(and_(Contact.user1_id == User.id, Contact.user2_id == g.user.id),
                      and_(Contact.user2_id == User.id, Contact.user1_id == g.user.id))). \
        filter(and_(User.full_name.ilike("%" + json['text'] + "%"),
                    User.id != g.user.id,
                    or_(Portal.id != None, Company.id != None))). \
        group_by(User.id, Contact.status). \
        order_by(expression.case([
        (or_(
            and_(Contact.status == Contact.STATUSES['REQUESTED_UNCONFIRMED'], User.id == g.user.id),
            and_(Contact.status == Contact.STATUSES['UNCONFIRMED_REQUESTED'], User.id != g.user.id)), '1'),
        (or_(
            and_(Contact.status == Contact.STATUSES['REQUESTED_UNCONFIRMED'], User.id != g.user.id),
            and_(Contact.status == Contact.STATUSES['UNCONFIRMED_REQUESTED'], User.id == g.user.id)), '2'),
        (or_(
            and_(Contact.status == Contact.STATUSES['ACTIVE_BANNED'], User.id == g.user.id),
            and_(Contact.status == Contact.STATUSES['BANNED_ACTIVE'], User.id != g.user.id)), '3'),
        (or_(
            and_(Contact.status == Contact.STATUSES['ACTIVE_BANNED'], User.id != g.user.id),
            and_(Contact.status == Contact.STATUSES['BANNED_ACTIVE'], User.id == g.user.id)), '4'),
        (or_(
            and_(Contact.status == Contact.STATUSES['ANY_REVOKED'], User.id == g.user.id),
            and_(Contact.status == Contact.STATUSES['REVOKED_ANY'], User.id != g.user.id)), 'X'),
        (or_(
            and_(Contact.status == Contact.STATUSES['ANY_REVOKED'], User.id != g.user.id),
            and_(Contact.status == Contact.STATUSES['REVOKED_ANY'], User.id == g.user.id)), 'X'),
        (Contact.status == Contact.STATUSES['ACTIVE_ACTIVE'], '5')
    ], else_='X'), User.full_name, User.id). \
        limit(PER_PAGE + 1).offset((json['page'] - 1) * PER_PAGE)

    users = query.all()
    next_page = (json['page'] + 1) if len(users) > PER_PAGE else False
    users = users[0:PER_PAGE]

    ret = []

    for u in users:
        user_dict = u.get_client_side_dict(fields='id,full_name,avatar.url,address_email')
        user_dict['common_portals_subscribed'] = [p.get_client_side_dict(fields='id,logo.url,host,name') for p in
                                                  u.active_portals_subscribed if
                                                  p.id in portals_ids]
        user_dict['common_companies_employers'] = [c.get_client_side_dict(fields='id,logo.url,name') for c in
                                                   u.active_companies_employers if
                                                   c.id in companies_ids]
        contact = g.db().query(Contact).filter_by(user1_id=min([u.id, g.user.id])).filter_by(
            user2_id=max([u.id, g.user.id])) \
            .first()
        if contact:
            user_dict['contact_status'] = contact.get_status_for_user(g.user.id)
        else:
            user_dict['contact_status'] = False
        ret.append(user_dict)

    return {
        'community': ret,
        'next_page': next_page
    }


@messenger_bp.route('/contacts_search/', methods=['OK'])
@check_right(UserIsActive)
def contacts_search(json):
    page_size = 100
    query = g.db.query(Contact.id, Contact.status, User). \
        outerjoin(User,
                  or_(and_(Contact.user1_id == User.id, Contact.user1_id != g.user.id),
                      and_(Contact.user2_id == User.id, Contact.user2_id != g.user.id))). \
        filter(and_(User.full_name.ilike("%" + json['text'] + "%"),
                    Contact.status.in_([Contact.STATUSES['ACTIVE_ACTIVE'], Contact.STATUSES['READONLY'],
                                        Contact.STATUSES['ACTIVE_BANNED'],
                                        Contact.STATUSES['BANNED_ACTIVE']]),
                    or_(Contact.user1_id == g.user.id, Contact.user2_id == g.user.id))). \
        order_by(expression.desc(Contact.last_message_tm)). \
        limit(page_size + 1).offset((json['page'] - 1) * page_size)

    contacts = query.all()
    next_page = (json['page'] + 1) if len(contacts) > page_size else False
    contacts = contacts[0:page_size]

    return {
        # 'unread_messages': unread_messages_count(g.user.id),
        'contacts': [{'chat_room_id': contact_id,
                      'unread_messages_count': User.get_unread_message_count(g.user.id, contact_id),
                      'chat_room_status': contact_status,
                      'users': [user.get_client_side_dict('id,full_name,avatar.url')]}
                     for (contact_id, contact_status, user) in contacts],
        'next_page': next_page
    }


@messenger_bp.route('/contact_action/', methods=['OK'])
@check_right(UserIsActive)
def contact_action(json):
    action = json['action']

    user1_id = min([g.user.id, json['user_id']])
    user2_id = max([g.user.id, json['user_id']])
    contact = g.db().query(Contact).filter_by(user1_id=user1_id, user2_id=user2_id).first()

    if contact:
        old_status_for_g_user = contact.get_status_for_user(g.user.id)

        if action == 'add' and old_status_for_g_user in [contact.STATUSES['ANY_REVOKED'],
                                                         contact.STATUSES['REVOKED_ANY']]:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REQUESTED_UNCONFIRMED'])
        elif action == 'remove' and old_status_for_g_user == contact.STATUSES['ACTIVE_ACTIVE']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REVOKED_ANY'])
        elif action == 'revoke' and old_status_for_g_user == contact.STATUSES['REQUESTED_UNCONFIRMED']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REVOKED_ANY'])
        elif action == 'confirm' and old_status_for_g_user == contact.STATUSES['UNCONFIRMED_REQUESTED']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['ACTIVE_ACTIVE'])
        elif action == 'unban' and old_status_for_g_user == contact.STATUSES['BANNED_ACTIVE']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['ACTIVE_ACTIVE'])
        else:
            raise BadDataProvided(
                "Wrong action `%s` for status `%s=>%s`" % (action, contact.status, old_status_for_g_user))
    else:
        if action == 'add':
            contact = Contact(user1_id=user1_id, user2_id=user2_id)
            contact.set_status_for_user(g.user.id, contact.STATUSES['REQUESTED_UNCONFIRMED'])
        else:
            raise BadDataProvided("Wrong action `add` for no contact")

    contact.save()
    # g.db.commit()

    return {'contact_status': contact.get_status_for_user(g.user.id)}
