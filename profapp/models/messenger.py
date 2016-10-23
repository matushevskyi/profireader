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
from utils.db_utils import db
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

        return {
            there_is_more[0]: there_is_more[1],
            'messages': messages
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
        return utils.dict_merge(self.get_client_side_dict(fields='id,content,from_user_id'),
                                {'timestamp': self.cr_tm.timestamp() if self.cr_tm else 0, 'chat_room_id': self.contact_id})


    @staticmethod
    def send_greeting_message(send_to_user):
        pass

# proficontact = g.db.query(Contact).filter_by(user1_id=RECORD_IDS.SYSTEM_USERS.profireader(), user2_id=send_to_user.id).one()
#        greetings = Message(from_user_id=RECORD_IDS.SYSTEM_USERS.profireader(), contact_id=proficontact.id,
#                           content=TranslateTemplate.getTranslate('profireader_messages', 'Welcome to profireader', '', True, send_to_user.lang),
#                            message_type=Message.MESSAGE_TYPES['PROFIREADER_NOTIFICATION'],
#                            message_subtype='WELCOME')
#        g.db.add(greetings)
#        g.db.commit()

#        proficontact = g.db.query(Contact).filter_by(user1_id=RECORD_IDS.SYSTEM_USERS.profireader(),
#                                                     user2_id=send_to_user.id).one()
#        greetings = Notification(to_user_id=RECORD_IDS.SYSTEM_USERS.profireader(), contact_id=proficontact.id,
#                            content=TranslateTemplate.translate_and_substitute(
#                                'profireader_notifications',
#                                'Welcome to profireader. We hope for fruitful collaboration. You can <a href="%(tutorial_url)s">see</a> short video instruction, and welcome to <a href="%(contact_url)s">contact</a> us',
#                                {'tutorial_url': '/tutorial/',
#                                 'contact_url': '/contact_us/'},
#                                url='',
#                                language=send_to_user.lang),
#                            message_type=Message.MESSAGE_TYPES['PROFIREADER_NOTIFICATION'],
#                            message_subtype='GREETING')
#        g.db.add(greetings)
#        g.db.commit()
