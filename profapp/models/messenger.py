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
from flask import g, session, app, current_app
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

    @staticmethod
    def send_message_behalf_of(user_id, message_text):

        pass


class Message(Base, PRBase):
    __tablename__ = 'message'

    MESSAGE_TYPES = {'MESSAGE': 'MESSAGE',
                     'PROFIREADER_NOTIFICATION': 'PROFIREADER_NOTIFICATION'}

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    read_tm = Column(TABLE_TYPES['timestamp'])

    from_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))
    contact_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Contact.id))
    content = Column(TABLE_TYPES['string_1000'])
    message_type = Column(TABLE_TYPES['string_100'])
    message_subtype = Column(TABLE_TYPES['string_100'])

    contact = relationship(Contact)

    @staticmethod
    def send_greeting_message(send_to_user):
         pass
#        proficontact = g.db.query(Contact).filter_by(user1_id=RECORD_IDS.SYSTEM_USERS.profireader(), user2_id=send_to_user.id).one()
#        greetings = Message(from_user_id=RECORD_IDS.SYSTEM_USERS.profireader(), contact_id=proficontact.id,
#                           content=TranslateTemplate.getTranslate('profireader_messages', 'Welcome to profireader', '', True, send_to_user.lang),
#                            message_type=Message.MESSAGE_TYPES['PROFIREADER_NOTIFICATION'],
#                            message_subtype='WELCOME')
#        g.db.add(greetings)
#        g.db.commit()

