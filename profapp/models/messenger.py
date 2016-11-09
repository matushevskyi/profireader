from sqlalchemy import Column, ForeignKey, text
from sqlalchemy.orm import relationship, aliased, backref
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..constants import RECORD_IDS
from ..models.company import Company, UserCompany
from ..models.portal import PortalDivision, Portal
from ..models.users import User
from ..models.files import File
from ..models.translate import TranslateTemplate
from ..models.tag import Tag, TagPortalDivision, TagPublication
from .pr_base import PRBase, Base, MLStripper, Grid
from tools.db_utils import db
from flask import g, session, app, current_app, url_for
from sqlalchemy.sql import or_, and_
import re
from sqlalchemy import event
from ..constants.SEARCH import RELEVANCE
from datetime import datetime
from .files import FileImg, FileImgDescriptor
from .. import utils
from .elastic import PRElasticField, PRElasticDocument
from config import Config
import simplejson
from ..controllers.errors import BadDataProvided
from sqlalchemy.sql import expression


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

    def get_status_for_user(self, user_id):
        if user_id == self.user1_id:
            return self.status
        else:
            splited = self.status.split('_')
            splited.reverse()
            return '_'.join(splited)

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

    informed_by_email_about_unread = Column(TABLE_TYPES['timestamp'])

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

    informed_by_email_about_unread = Column(TABLE_TYPES['timestamp'])

    to_user = relationship(User)

    NOTIFICATION_TYPES = {
        'GREETING': 'GREETING', 'CUSTOM': 'CUSTOM',
        'FRIEND_REQUEST_ACTIVITY': 'FRIEND_REQUEST_ACTIVITY',
        'MATERIAL_PUBLICATION_STATUS_CHANGED': 'MATERIAL_PUBLICATION_STATUS_CHANGED'
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

    @staticmethod
    def notification_delivered(*args, **kwargs):
        print('notification_delivered', args, kwargs)

    @staticmethod
    def notification_send(notification_data):
        from socketIO_client import SocketIO
        from config import MAIN_DOMAIN

        with SocketIO('socket.' + MAIN_DOMAIN, 80) as socketIO:
            socketIO.emit('send_notification', notification_data, Notification.notification_delivered)
            socketIO.wait_for_callbacks(seconds=1)

    @staticmethod
    def contact_request_send(to_user_id, from_user_id, status):
        from socketIO_client import SocketIO
        from config import MAIN_DOMAIN


        with SocketIO('socket.' + MAIN_DOMAIN, 80) as socketIO:
            socketIO.emit('send_contact_requested', {'to_user_id': to_user_id, 'from_user_id': from_user_id,
                                                     'status': status},
                          Notification.notification_delivered)
            socketIO.wait_for_callbacks(seconds=1)


    @staticmethod
    def send_greeting(to_user):
        Notification.notification_send({'to_user_id': to_user.id,
                                        'content': TranslateTemplate.translate_and_substitute(
                                            template='_NOTIFICATIONS',
                                            url='',
                                            language=to_user.lang,
                                            allow_html='*',
                                            phrase="Welcome to profireader. You can change your profile %(url_profile)s",
                                            dictionary={
                                                'to_user': to_user.get_client_side_dict(fields='full_name'),
                                                'url_profile': url_for(
                                                    'user.profile',
                                                    user_id=to_user.id)}),
                                        'notification_type': Notification.NOTIFICATION_TYPES['GREETING']
                                        })

    @staticmethod
    def send_custom(to_user, text):
        Notification.notification_send({'to_user_id': to_user.id,
                                        'notification_type': Notification.NOTIFICATION_TYPES['CUSTOM']
                                        })


    @staticmethod
    def send_friend_request_activity(to_user, from_user, new_status, old_status):
        if new_status == old_status:
            return

        phrase = None

        if new_status == Contact.STATUSES['ACTIVE_ACTIVE'] and old_status == Contact.STATUSES['REQUESTED_UNCONFIRMED']:
            phrase = "User %(from_user.full_name)s accepted your friendship request :)"
        elif new_status == Contact.STATUSES['ANY_REVOKED'] and old_status == Contact.STATUSES['ACTIVE_ACTIVE']:
            phrase = "User %(from_user.full_name)s revoked your friendship :("

        if phrase:
            Notification.notification_send({'to_user_id': to_user.id,
                                            'content': TranslateTemplate.translate_and_substitute(
                                                template='_NOTIFICATIONS',
                                                url='',
                                                language=to_user.lang,
                                                allow_html='*',
                                                phrase=phrase,
                                                dictionary={
                                                    'to_user': to_user.get_client_side_dict(fields='full_name'),
                                                    'from_user': from_user.get_client_side_dict(fields='full_name'),
                                                }),
                                            'notification_type': Notification.NOTIFICATION_TYPES[
                                                'FRIEND_REQUEST_ACTIVITY']
                                            })


        Notification.contact_request_send(to_user.id, from_user.id, new_status)


@event.listens_for(Notification.content, "set")
def set_notification_content(target, value, oldvalue, initiator):
    target.content_stripped = MLStripper().strip_tags(value)
