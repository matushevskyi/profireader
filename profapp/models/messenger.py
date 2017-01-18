from flask import g, url_for
from sqlalchemy import Column, ForeignKey
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_
from sqlalchemy.sql import expression

from profapp import on_value_changed
from .pr_base import PRBase, Base
from .. import utils
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..controllers.errors import BadDataProvided
from ..models.translate import TranslateTemplate
from ..models.users import User


class Socket:
    @staticmethod
    def notification_delivered(*args, **kwargs):
        print('notification_delivered', args, kwargs)

    @staticmethod
    def request_status_changed(to_user_id, from_user_id, status):
        from socketIO_client import SocketIO
        from config import MAIN_DOMAIN

        with SocketIO('socket.' + MAIN_DOMAIN, 80) as socketIO:
            socketIO.emit('request_status_changed',
                          {'to_user_id': to_user_id, 'from_user_id': from_user_id, 'status': status},
                          Socket.notification_delivered)
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def notification(notification_data):
        from socketIO_client import SocketIO
        from config import MAIN_DOMAIN

        with SocketIO('socket.' + MAIN_DOMAIN, 80) as socketIO:
            socketIO.emit('send_notification', notification_data, Socket.notification_delivered)
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def prepare_notifications(to_users, notification_type, phrases, dict_main={}, except_to_user=[],
                              phrases_comment=None,
                              phrases_default=None):

        if not phrases:
            return utils.do_nothing

        from_user_dict = {'from_user': g.user.get_client_side_dict(fields='full_name'),
                          'url_profile_from_user': url_for('user.profile', user_id=g.user.id)} if getattr(g, 'user',
                                                                                                          None) else {}

        if isinstance(phrases, str):
            phrases = [phrases]
        if isinstance(dict_main, dict):
            dict_main = [dict_main for k in phrases]

        if isinstance(phrases_comment, str):
            phrases_comment = [phrases_comment for k in phrases]
        if not isinstance(phrases_comment, dict):
            phrases_comment = ['' for k in phrases]

        if isinstance(phrases_default, str):
            phrases_default = [phrases_default for k in phrases]
        if not isinstance(phrases_default, dict):
            phrases_default = [None for k in phrases]

        datas = [{'to_user_id': u.id,
                  'content': '<br/>'.join([TranslateTemplate.translate_and_substitute(
                      template='_NOTIFICATIONS', url='', language=u.lang, allow_html='*',
                      phrase=phrase, phrase_comment=phrases_comment[ind], phrase_default=phrases_default[ind],
                      dictionary=utils.dict_merge(dict_main[ind], from_user_dict,
                                                  {'to_user': u.get_client_side_dict(fields='full_name'),
                                                   'url_profile_to_user': url_for('user.profile', user_id=u.id)}))
                                           for ind, phrase in enumerate(phrases)]),
                  'notification_type': notification_type
                  } for u in list(set(to_users) - set(except_to_user))] if phrases else []

        def ret():
            for d in datas:
                Socket.notification(d)

        return ret

    @staticmethod
    def send_greeting(to_users):
        # possible notification - 1
        return Socket.prepare_notifications(to_users, Notification.NOTIFICATION_TYPES['GREETING'],
                                            "Welcome to profireader. You can change %s or get a look at %s" % \
                                            (utils.jinja.link('url_profile_to_user', 'your profile', True),
                                             utils.jinja.link('url_tutorial', 'tutorial', True)),
                                            dict_main={'url_tutorial': url_for('tutorial.index')})()


class Contact(Base, PRBase):
    __tablename__ = 'contact'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    last_message_tm = Column(TABLE_TYPES['timestamp'])

    user1_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))
    user2_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))

    status = Column(TABLE_TYPES['string_30'])

    STATUSES = {'ACTIVE_ACTIVE': 'ACTIVE_ACTIVE',
                'REQUESTED_UNCONFIRMED': 'REQUESTED_UNCONFIRMED',
                'UNCONFIRMED_REQUESTED': 'UNCONFIRMED_REQUESTED',
                'ACTIVE_BANNED': 'ACTIVE_BANNED',
                'BANNED_ACTIVE': 'BANNED_ACTIVE',
                'ANY_REVOKED': 'ANY_REVOKED',
                'REVOKED_ANY': 'REVOKED_ANY',
                'READONLY': 'READONLY'
                }

    def get_another_user_id(self, user_id):
        if user_id == self.user1_id:
            return self.user2_id
        elif user_id == self.user2_id:
            return self.user1_id
        else:
            raise BadDataProvided("User with id=`%s` is not presented in contact with id=`%s`" % (user_id, self.id))

    def get_client_side_dict(self, fields='id,user1_id,user2_id,status', more_fields=None):
        return self.to_dict(fields, more_fields)

    def get_status_for_user(self, user_id, for_status=None):
        st = for_status if for_status else self.status
        if user_id == self.user1_id:
            return st
        elif user_id == self.user2_id:
            spliced = st.split('_')
            spliced.reverse()
            return '_'.join(spliced)
        else:
            raise BadDataProvided("User with id=`%s` is not presented in contact with id=`%s`" % (user_id, self.id))

    def set_status_for_user(self, user_id, status):
        if user_id == self.user1_id:
            self.status = status
        else:
            splited = status.split('_')
            splited.reverse()
            self.status = '_'.join(splited)
        return self

    def get_messages(self, count, get_older=False, than_id=None):
        messages_filter = (Message.contact_id == self.id)
        messages_query = g.db().query(Message)
        if than_id:
            if get_older:
                messages = messages_query.filter(and_(messages_filter, Message.id < than_id)).order_by(
                    expression.desc(Message.cr_tm)).limit(count + 1).all()
                there_is_more = ['there_is_older', len(messages) > count]
                messages = messages[0:count]
                # messages.reverse()

            else:
                messages = messages_query.filter(and_(messages_filter, Message.id > than_id)).order_by(
                    expression.asc(Message.cr_tm)).limit(count + 1).all()
                there_is_more = ['there_is_newer', len(messages) > count]
                messages = messages[0:count]

        else:
            messages = messages_query.filter(messages_filter).order_by(expression.desc(Message.cr_tm)).limit(
                count + 1).all()
            there_is_more = ['there_is_older', len(messages) > count]
            messages = messages[0:count]
            # messages.reverse()

        return {
            there_is_more[0]: there_is_more[1],
            'items': messages
        }


@on_value_changed(Contact.status)
def contact_status_changed(target, new_value, old_value, action):
    # send contact request messages via socketIO (to both users)
    def ret():
        Socket.request_status_changed(target.user1_id, target.user2_id,
                                      target.get_status_for_user(target.user1_id, new_value))
        Socket.request_status_changed(target.user2_id, target.user1_id,
                                      target.get_status_for_user(target.user2_id, new_value))

    return ret


@on_value_changed(Contact.status)
def contact_status_changed_2(target, new_value, old_value, action):
    # send notifications
    to_user = User.get(target.get_another_user_id(g.user.id))

    new_status = target.get_status_for_user(to_user.id, new_value) if new_value else None
    old_status = target.get_status_for_user(to_user.id, old_value) if old_value else None

    if new_status == Contact.STATUSES['ACTIVE_ACTIVE'] and old_status == Contact.STATUSES['REQUESTED_UNCONFIRMED']:
        phrase = "User %s accepted your friendship request :)" % (utils.jinja.link_user_profile(),)
    elif new_status == Contact.STATUSES['ANY_REVOKED'] and old_status == Contact.STATUSES['ACTIVE_ACTIVE']:
        phrase = "User %s revoked your friendship :(" % (utils.jinja.link_user_profile(),)
    else:
        phrase = None

    # possible notification - 2
    return Socket.prepare_notifications([to_user], Notification.NOTIFICATION_TYPES['FRIEND_REQUEST_ACTIVITY'], phrase,
                                        phrases_comment='This message is sent to user when friendship request status is changed from `%s` to `%s`' % (
                                            old_value, new_value))


class Message(Base, PRBase):
    __tablename__ = 'message'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    read_tm = Column(TABLE_TYPES['timestamp'])

    from_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))
    contact_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Contact.id))
    content = Column(TABLE_TYPES['string_1000'])

    contact = relationship(Contact)

    def client_message(self):
        ret = utils.dict_merge(self.get_client_side_dict(fields='id,content,from_user_id'),
                               {'cr_tm': self.cr_tm.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                                'chat_room_id': self.contact_id})
        return ret


class Notification(Base, PRBase):
    __tablename__ = 'notification'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    read_tm = Column(TABLE_TYPES['timestamp'])

    to_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))
    content = Column(TABLE_TYPES['string_1000'])
    content_stripped = Column(TABLE_TYPES['string_1000'])
    notification_type = Column(TABLE_TYPES['string_100'])
    notification_data = Column(TABLE_TYPES['json'])

    # informed_by_email_about_unread = Column(TABLE_TYPES['timestamp'])

    to_user = relationship(User)

    NOTIFICATION_TYPES = {
        'GREETING': 'GREETING', 'CUSTOM': 'CUSTOM',
        'FRIEND_REQUEST_ACTIVITY': 'FRIEND_REQUEST_ACTIVITY',
        'COMPANY_EMPLOYERS_ACTIVITY': 'COMPANY_EMPLOYERS_ACTIVITY',
        'COMPANY_PORTAL_MEMBEREE_ACTIVITY': 'COMPANY_PORTAL_MEMBEREE_ACTIVITY',
        'PUBLICATION_ACTIVITY': 'PUBLICATION_ACTIVITY',
        'PORTAL_COMPANIES_MEMBERS_ACTIVITY': 'PORTAL_COMPANIES_MEMBERS_ACTIVITY'
    }

    @staticmethod
    def get_notifications(count, to_user_id, get_older=False, than_id=None):
        notification_query = g.db().query(Notification).filter(Notification.to_user_id == to_user_id)
        if than_id:
            if get_older:
                notifications = notification_query.filter(Notification.id < than_id).order_by(
                    expression.desc(Notification.cr_tm)).limit(count + 1).all()
                there_is_more = ['there_is_older', len(notifications) > count]
                notifications = notifications[0:count]
                # notifications.reverse()
            else:
                notifications = notification_query.filter(Notification.id > than_id).order_by(
                    expression.asc(Notification.cr_tm)).limit(count + 1).all()
                there_is_more = ['there_is_newer', len(notifications) > count]
                notifications = notifications[0:count]

        else:
            notifications = notification_query.order_by(expression.desc(Notification.cr_tm)).limit(
                count + 1).all()
            there_is_more = ['there_is_older', len(notifications) > count]
            notifications = notifications[0:count]
            # notifications.reverse()

        return {
            there_is_more[0]: there_is_more[1],
            'items': notifications
        }

    def client_message(self):
        ret = utils.dict_merge(self.get_client_side_dict(fields='id,content,notification_type,to_user_id'),
                               {'cr_tm': self.cr_tm.strftime("%a, %d %b %Y %H:%M:%S GMT")})
        return ret


@event.listens_for(Notification.content, "set")
def set_notification_content(target, value, oldvalue, initiator):
    target.content_stripped = utils.strip_tags(value)
