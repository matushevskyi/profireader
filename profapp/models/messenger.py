from flask import g, url_for
from sqlalchemy import Column, ForeignKey
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_
from sqlalchemy.sql import expression

from .pr_base import PRBase, Base
from .. import utils
from ..constants.TABLE_TYPES import TABLE_TYPES
# from ..controllers.errors import BadDataProvided
from ..models.users import User
from ..constants.APPLICATION_PORTS import APPLICATION_PORTS
from ..models import exceptions


class Socket:


    @staticmethod
    def notification_delivered(ack_id, notification_name, *args, **kwargs):
        print('notification_delivered (ack_id={})'.format(ack_id), notification_name, args, kwargs)

    @staticmethod
    def request_status_changed(to_user_id, from_user_id, status):
        from socketIO_client import SocketIO

        with SocketIO('socket.profi', APPLICATION_PORTS['socket']) as socketIO:
            socketIO.emit('request_status_changed',
                          {'to_user_id': to_user_id, 'from_user_id': from_user_id, 'status': status},
                          lambda ack_id: Socket.notification_delivered(
                              ack_id, 'request_status_changed',
                              {'to_user_id': to_user_id, 'from_user_id': from_user_id, 'status': status}))
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def notification(notification_data):
        from socketIO_client import SocketIO

        with SocketIO('socket.profi', APPLICATION_PORTS['socket']) as socketIO:
            socketIO.emit('send_notification', notification_data,
                          lambda ack_id: Socket.notification_delivered(ack_id, 'send_notification', notification_data))
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def insert_translation(data):
        from socketIO_client import SocketIO
        with SocketIO('socket.profi', APPLICATION_PORTS['socket']) as socketIO:
            socketIO.emit('insert_translation', data,
                          lambda ack_id: Socket.notification_delivered(ack_id, 'insert_translation', data))
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def update_translation(id, data):
        from socketIO_client import SocketIO
        from config import MAIN_DOMAIN
        with SocketIO('socket.profi', APPLICATION_PORTS['socket']) as socketIO:
            socketIO.emit('update_translation', {'id': id, 'data': data},
                          lambda ack_id: Socket.notification_delivered(ack_id, 'update_translation',
                                                                       {'id': id, 'data': data}))
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def prepare_notifications(to_users, notification_type, phrases, except_to_user=[]):

        if not phrases or not to_users:
            return utils.do_nothing

        from_user_dict = {'from_user': g.user.get_client_side_dict(fields='full_name'),
                          'url_profile_from_user': url_for('user.profile', user_id=g.user.id)} if getattr(g, 'user',
                                                                                                          None) else {}
        if not isinstance(phrases, list):
            phrases = [phrases]

        datas = [{'to_user_id': u.id,
                  'content': '<br/>'.join([phrase.translate(
                      template='_NOTIFICATIONS', allow_html='*', language=u.lang,
                      more_dictionary=
                      utils.dict_merge(from_user_dict, {
                          'to_user': u.get_client_side_dict(fields='full_name'),
                          'url_profile_to_user': url_for('user.profile', user_id=u.id)}))
                                           for ind, phrase in enumerate(phrases)]),
                  'notification_type': notification_type}
                 for u in list(set(to_users) - set(except_to_user))] if phrases else []

        for d in datas:
            g.call_after_commit.append(lambda d=d: Socket.notification(d))

        return utils.do_nothing()


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
            raise exceptions.BadDataProvided("User with id=`%s` is not presented in contact with id=`%s`" % (user_id, self.id))

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
            raise exceptions.BadDataProvided("User with id=`%s` is not presented in contact with id=`%s`" % (user_id, self.id))

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
    content = Column(TABLE_TYPES['string_65535'])
    content_stripped = Column(TABLE_TYPES['string_65535'])
    notification_type = Column(TABLE_TYPES['string_100'])
    notification_data = Column(TABLE_TYPES['json'])

    # informed_by_email_about_unread = Column(TABLE_TYPES['timestamp'])

    to_user = relationship(User)

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
