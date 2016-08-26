from .blueprints_declaration import messenger_bp
from flask import render_template, request, url_for, g, redirect, abort
from .request_wrapers import check_right
from .errors import BadDataProvided

# # from ..models.bak_articles import ArticleCompany, ArticlePortalDivision
from utils.db_utils import db
# from .pagination import pagination
# from config import Config
# from .. import utils
from ..models.users import User
from ..models.company import Company, UserCompany
from ..models.portal import Portal, UserPortalReader
from ..models.messenger import Contact, Message

from ..models.rights import EditCompanyRight, EmployeesRight, EditPortalRight, UserIsEmployee, EmployeeAllowRight, \
    CanCreateCompanyRight, UserIsActive, BaseRightsEmployeeInCompany

from sqlalchemy import and_, or_
from sqlalchemy.sql import expression
from .. import utils


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
    portals_ids = []
    for p in g.user.active_portals_subscribed:
        portals_ids.append(p.id)

    companies_ids = []
    for c in g.user.active_companies_employers:
        companies_ids.append(c.id)

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
        filter(and_(User.full_name.ilike("%" + json['text'] + "%"),
                    User.id != g.user.id,
                    or_(Portal.id != None, Company.id != None))). \
        group_by(User.id). \
        order_by(User.full_name). \
        limit(11).offset((json['page'] - 1) * 10)

    users = query.all()
    next_page = (json['page'] + 1) if len(users) > 10 else False
    users = users[0:10]

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
    query = g.db.query(Contact, User). \
        outerjoin(User,
                  or_(and_(Contact.user1_id == User.id, Contact.user1_id != g.user.id),
                      and_(Contact.user2_id == User.id, Contact.user2_id != g.user.id))). \
        filter(and_(Contact.status == Contact.STATUSES['ACTIVE_ACTIVE'],
                    or_(Contact.user1_id == g.user.id, Contact.user2_id == g.user.id))). \
        limit(51).offset((json['page'] - 1) * 50)

    # from sqlalchemy.dialects import postgresql

    contacts = query.all()
    next_page = (json['page'] + 1) if len(contacts) > 50 else False
    contacts = contacts[0:50]

    ret = []

    for (c, u) in contacts:
        user_dict = u.get_client_side_dict(more_fields='avatar')
        ret.append(user_dict)

    return {
        'contacts': ret,
        'next_page': next_page
    }


# def group_messages_by_session(chat_room_id, messages, count, if_more_then):
#     def client_message(m: Message):
#         return m.get_client_side_dict(fields='id,content,from_user_id,cr_tm')
#
#     return {
#         'chat_room_id': chat_room_id,
#         'users': {
#             chat_room_id: User.get(chat_room_id).get_client_side_dict(more_fields='avatar'),
#             g.user.id: User.get(g.user.id).get_client_side_dict(more_fields='avatar'),
#         },
#         if_more_then: len(messages) > count,
#         'messages_by_session': [
#             {'session_id': m.id,
#              'session_name': ('chat session %s' % (m.id,)),
#              'messages': [client_message(m)]}
#             for m in messages[0:count]]
#     }


def get_messages(user_id, count, get_older=False, than_id=None):
    messages_filter = or_(Contact.user1_id == user_id, Contact.user2_id == user_id)
    messages_query = g.db().query(Message). \
        outerjoin(Contact, or_(Message.from_user_id == Contact.user1_id, Message.from_user_id == Contact.user2_id))
    if than_id:
        if get_older:
            messages = messages_query.filter(and_(messages_filter, Message.id < than_id)).order_by(
                expression.desc(Message.id)).limit(count + 1).all()
            messages.reverse()
            there_is_more = 'there_is_older'
        else:
            messages = messages_query.filter(and_(messages_filter, Message.id > than_id)).order_by(
                expression.asc(Message.id)).limit(count + 1).all()
            there_is_more = 'there_is_newer'
    else:
        messages = messages_query.filter(messages_filter).order_by(expression.desc(Message.id)).limit(count).all()
        messages.reverse()
        there_is_more = 'there_is_older'

    def client_message(m: Message):
        return utils.dict_merge(m.get_client_side_dict(fields='id,content,from_user_id,cr_tm'), {'timestamp': m.cr_tm.timestamp()})

    return {
        'chat_room_id': user_id,
        'users': {
            user_id: User.get(user_id).get_client_side_dict(more_fields='avatar'),
            g.user.id: User.get(g.user.id).get_client_side_dict(more_fields='avatar'),
        },
        there_is_more: len(messages) > count,
        'messages': [client_message(m) for m in messages[0:count]]
    }

    # return messages


@messenger_bp.route('/send_message/', methods=['OK'])
@check_right(UserIsActive)
def send_message(json):
    chat_with_user_id = json['chat_room_id']
    user1_id = min([g.user.id, chat_with_user_id])
    user2_id = max([g.user.id, chat_with_user_id])
    contact = g.db().query(Contact).filter_by(user1_id=user1_id, user2_id=user2_id).first()
    message = Message(contact_id=contact.id, content=json['text'], from_user_id=g.user.id)
    message.save()
    return get_messages(chat_with_user_id, 100, get_older=False, than_id=json['last_message_id'])


@messenger_bp.route('/refresh_chats/', methods=['OK'])
@check_right(UserIsActive)
def refresh_chats(json):
    pass


@messenger_bp.route('/load_chat/', methods=['OK'])
@check_right(UserIsActive)
def load_chat(json):
    chat_with_user_id = json['chat_room_id']
    return get_messages(chat_with_user_id, 100)


def aaa():
    # chat room == user
    ret = {}

    message = None
    if json['chat_room_id'] is not None:
        chat_with_user_id = json['chat_room_id']
        if json['text']:
            user1_id = min([g.user.id, chat_with_user_id])
            user2_id = max([g.user.id, chat_with_user_id])
            contact = g.db().query(Contact).filter_by(user1_id=user1_id, user2_id=user2_id).first()
            message = Message(contact_id=contact.id, content=json['text'], from_user_id=g.user.id)
            message.save()

        if json['load_last_messages_for_chat_room']:
            messages_filter = or_(Contact.user1_id == chat_with_user_id, Contact.user2_id == chat_with_user_id)
            messages_query = g.db().query(Message). \
                outerjoin(Contact,
                          or_(Message.from_user_id == Contact.user1_id, Message.from_user_id == Contact.user2_id))
            messages = messages_query.filter(messages_filter).order_by(expression.desc(Message.id)).limit(101).all()
            messages.reverse()
            ret['load_last_messages_for_chat_room'] = group_messages_by_session(chat_with_user_id, messages, 100,
                                                                                if_more_then='there_is_older')

    ret['check_for_new_messages_also_for_chat_rooms'] = []

    for userchat_room_id_and_last_message_id in json['check_for_new_messages_also_for_chat_rooms']:
        chat_room_id = userchat_room_id_and_last_message_id['chat_room_id']
        last_message_id = userchat_room_id_and_last_message_id['last_message_id']
        messages_filter = or_(Contact.user1_id == chat_room_id, Contact.user2_id == chat_room_id)
        messages_query = g.db().query(Message). \
            outerjoin(Contact, or_(Message.from_user_id == Contact.user1_id, Message.from_user_id == Contact.user2_id))
        if last_message_id is None:
            messages = messages_query.filter(messages_filter). \
                order_by(expression.desc(Message.id)).limit(101).all()
        else:
            messages = messages_query.filter(and_(Message.id > last_message_id, messages_filter)). \
                order_by(expression.asc(Message.id)).limit(101).all()
        ret['check_for_new_messages_also_for_chat_rooms'].append(group_messages_by_session(chat_room_id, messages, 100,
                                                                                           if_more_then='there_is_newer'))

    return ret


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
