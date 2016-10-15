from .blueprints_declaration import messenger_bp
from flask import render_template, request, url_for, g, redirect, abort
from .request_wrapers import check_right
from .errors import BadDataProvided
from sqlalchemy import func

from ..constants import RECORD_IDS

from utils.db_utils import db
from ..models.users import User
from ..models.company import Company, UserCompany
from ..models.portal import Portal, UserPortalReader
from ..models.messenger import Contact, Message

from ..models.rights import EditCompanyRight, EmployeesRight, EditPortalRight, UserIsEmployee, EmployeeAllowRight, \
    CanCreateCompanyRight, UserIsActive, BaseRightsEmployeeInCompany

from sqlalchemy import and_, or_
from sqlalchemy.sql import expression
from .. import utils
from sqlalchemy import update
import datetime


@messenger_bp.route('/', methods=['GET'])
@check_right(UserIsActive)
def messenger():
    return render_template('messenger/messenger.html', PROFIREADER_USER_ID=RECORD_IDS.SYSTEM_USERS.profireader())


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
                  or_(Contact.user1_id == User.id, Contact.user2_id == User.id)). \
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
        (Contact.status == Contact.STATUSES['ACTIVE_ACTIVE'], 'Z')
    ], else_='X'), User.full_name). \
        limit(PER_PAGE + 1).offset((json['page'] - 1) * PER_PAGE)

    users = query.all()
    next_page = (json['page'] + 1) if len(users) > PER_PAGE else False
    users = users[0:PER_PAGE]

    ret = []

    for u in users:
        user_dict = u.get_client_side_dict(more_fields='avatar')
        user_dict['common_portals_subscribed'] = [p.get_client_side_dict() for p in u.active_portals_subscribed if
                                                  p.id in portals_ids]
        user_dict['common_companies_employers'] = [c.get_client_side_dict() for c in u.active_companies_employers if
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


def get_messages_and_unread_count(chat_room_id, count, get_older=False, than_id=None):
    ret = {}
    if chat_room_id:
        contact = Contact.get(chat_room_id)
        messages_filter = (Message.contact_id == chat_room_id)
        messages_query = g.db().query(Message)
        if than_id:
            if get_older:
                messages = messages_query.filter(and_(messages_filter, Message.id < than_id)).order_by(
                    expression.desc(Message.id)).limit(count + 1).all()
                there_is_more = ['there_is_older', len(messages) > count]
                messages = messages[0:count]
                messages.reverse()

            else:
                messages = messages_query.filter(and_(messages_filter, Message.id > than_id)).order_by(
                    expression.asc(Message.id)).limit(count + 1).all()
                there_is_more = ['there_is_newer', len(messages) > count]
                messages = messages[0:count]

        else:
            messages = messages_query.filter(messages_filter).order_by(expression.desc(Message.id)).limit(
                count + 1).all()
            there_is_more = ['there_is_older', len(messages) > count]
            messages = messages[0:count]
            messages.reverse()

        def client_message(m: Message):
            return utils.dict_merge(m.get_client_side_dict(fields='id,content,from_user_id,cr_tm'),
                                    {'timestamp': m.cr_tm.timestamp()})
            return ret

        another_user_id = contact.user1_id if g.user.id == contact.user2_id else contact.user2_id

        read_ids = [m.id for m in messages if m.from_user_id != g.user.id and not m.read_tm]

        if len(read_ids):
            g.db().execute(
                "SELECT message_set_read('%s', '%s', ARRAY ['%s']);" % (g.user.id, contact.id, "', '".join(read_ids)))
            g.db().execute("SELECT message_notify_unread('%s', '%s');" % (g.user.id, contact.id))

        ret['chat_room'] = {
            'chat_room_id': chat_room_id,
            'chat_room_status': contact.status,
            'users': {
                g.user.id: User.get(g.user.id).get_client_side_dict(more_fields='avatar'),
                another_user_id: User.get(another_user_id).get_client_side_dict(more_fields='avatar')
            },
            there_is_more[0]: there_is_more[1],
            'messages': [client_message(m) for m in messages]
        }
    # ret['unread_messages'] = unread_messages_count(g.user.id)
    return ret


def unread_messages_count(user_id):
    messages_count = g.db().query(Contact.id, func.count(Contact.id)).outerjoin(Message,
                                                                                and_(Message.contact_id == Contact.id,
                                                                                     Message.read_tm == None,
                                                                                     Message.from_user_id != user_id
                                                                                     )). \
        filter(and_(Message.id != None, or_(Contact.user2_id == user_id, Contact.user1_id == user_id))). \
        group_by(Contact.id).all()

    return {contact_id: contact_count for (contact_id, contact_count) in messages_count}


MESSANGER_MESSGES_PER_LOAD = 5


@messenger_bp.route('/send_message/', methods=['OK'])
@check_right(UserIsActive)
def send_message(json):
    contact = Contact.get(json['chat_room_id'])
    if contact.user1_id == g.user.id or contact.user2_id == g.user.id:
        message = Message(contact_id=contact.id, content=json['text'], from_user_id=g.user.id)
        message.save()
        return get_messages_and_unread_count(contact.id, MESSANGER_MESSGES_PER_LOAD, get_older=False,
                                             than_id=json['last_message_id'])
    else:
        raise BadDataProvided



@messenger_bp.route('/load_messages/', methods=['OK'])
@check_right(UserIsActive)
def load_messages(json):
    newer = json.get('newer', False)
    return get_messages_and_unread_count(json['chat_room_id'], MESSANGER_MESSGES_PER_LOAD, get_older=False if newer else True,
                                         than_id=json.get('last_message_id' if newer else 'first_message_id', None))


@messenger_bp.route('/contact_action/', methods=['OK'])
@check_right(UserIsActive)
def contact_action(json):
    action = json['action']

    user1_id = min([g.user.id, json['user_id']])
    user2_id = max([g.user.id, json['user_id']])
    contact = g.db().query(Contact).filter_by(user1_id=user1_id, user2_id=user2_id).first()

    if contact:
        status_for_action_user = contact.get_status_for_user(g.user.id)
        if action == 'add' and status_for_action_user in [contact.STATUSES['ANY_REVOKED'],
                                                          contact.STATUSES['REVOKED_ANY']]:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REQUESTED_UNCONFIRMED'])
        elif action == 'remove' and status_for_action_user == contact.STATUSES['ACTIVE_ACTIVE']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REVOKED_ANY'])
        elif action == 'revoke' and status_for_action_user == contact.STATUSES['REQUESTED_UNCONFIRMED']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['REVOKED_ANY'])
        elif action == 'confirm' and status_for_action_user == contact.STATUSES['UNCONFIRMED_REQUESTED']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['ACTIVE_ACTIVE'])
        elif action == 'unban' and status_for_action_user == contact.STATUSES['BANNED_ACTIVE']:
            contact.set_status_for_user(g.user.id, contact.STATUSES['ACTIVE_ACTIVE'])
        else:
            raise BadDataProvided(
                "Wrong action `%s` for status `%s=>%s`" % (action, contact.status, status_for_action_user))
    else:
        if action == 'add':
            contact = Contact(user1_id=user1_id, user2_id=user2_id)
            contact.set_status_for_user(g.user.id, 'REQUESTED_UNCONFIRMED')
        else:
            raise BadDataProvided("Wrong action `add` for no contact")

    contact.save()

    return {'contact_status': contact.get_status_for_user(g.user.id)}
