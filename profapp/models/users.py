from flask import request, current_app, g, flash, url_for
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from flask import session, json
from urllib import request as req
from config import Config
from ..controllers import errors
import re
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..constants import REGEXP
from ..constants.SOCIAL_NETWORKS import SOCIAL_NETWORKS, SOC_NET_NONE
from ..constants.USER_REGISTERED import REGISTERED_WITH_FLIPPED, REGISTERED_WITH
from ..constants import RECORD_IDS
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from tools.db_utils import db
from sqlalchemy import String
from . import country
import hashlib
from flask.ext.login import UserMixin
from .pr_base import PRBase, Base
from ..constants.SEARCH import RELEVANCE
from .. import utils
from flask import url_for, render_template
from ..utils import email_utils
from tools import db_utils

import random
import time
from .files import FileImg, FileImgDescriptor
from flask.ext.login import logout_user, current_user, login_user
from sqlalchemy import func


class User(Base, UserMixin, PRBase):
    __tablename__ = 'user'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    # personal_folder_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))
    system_folder_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))
    address_email = Column(TABLE_TYPES['email'], unique=True, index=True)

    first_name = Column(TABLE_TYPES['string_100'])
    last_name = Column(TABLE_TYPES['string_100'])
    full_name = Column(TABLE_TYPES['string_200'])

    # full_name = Column(TABLE_TYPES['name'])
    gender = Column(TABLE_TYPES['gender'])
    address_url = Column(TABLE_TYPES['string_1000'])
    address_phone = Column(TABLE_TYPES['phone'])
    about = Column(TABLE_TYPES['text'])
    address_city = Column(TABLE_TYPES['string_30'])
    address_location = Column(TABLE_TYPES['string_500'], default='', nullable=False)
    lang = Column(String(2), default='uk')

    email_confirmed = Column(TABLE_TYPES['boolean'], default=False, nullable=False)
    banned = Column(TABLE_TYPES['boolean'], default=False, nullable=False)

    birth_tm = Column(TABLE_TYPES['date'])
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    last_seen_tm = Column(TABLE_TYPES['timestamp'], default=datetime.datetime.utcnow)

    # profireader_avatar_url = Column(TABLE_TYPES['url'], nullable=False,
    #                                 default='//static.profireader.com/static/no_avatar.png')
    # profireader_small_avatar_url = Column(TABLE_TYPES['url'], nullable=False,
    #                                       default='//static.profireader.com/static/no_avatar_small.png')

    avatar_selected_preset = Column(TABLE_TYPES['string_30'], nullable=True)
    avatar_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    avatar_file_img = relationship(FileImg, uselist=False)

    # TODO: OZ by OZ: some condition about active
    active_portals_subscribed = relationship('Portal',
                                             viewonly=True,
                                             primaryjoin='User.id == UserPortalReader.user_id',
                                             secondary='reader_portal',
                                             secondaryjoin="and_(UserPortalReader.portal_id == Portal.id, Portal.status == 'ACTIVE', UserPortalReader.status == 'active')")

    active_companies_employers = relationship('Company',
                                              viewonly=True,
                                              primaryjoin='User.id == UserCompany.user_id',
                                              secondary='user_company',
                                              secondaryjoin="and_(UserCompany.company_id == Company.id, Company.status == 'ACTIVE', UserCompany.status == 'ACTIVE')")

    def set_avatar_preset(self, r, v):
        if v['selected_by_user']['type'] == 'preset':
            self.avatar_selected_preset = v['selected_by_user']['preset_id']
            v['selected_by_user']['type'] = 'none'
        else:
            self.avatar_selected_preset = None
        return v

    def get_avatar_preset(self, r, v):
        v['cropper']['preset_urls'] = {'gravatar': self.gravatar(size=300)}
        if self.avatar_selected_preset is not None:
            v['selected_by_user']['type'] = 'preset'
            v['selected_by_user']['preset_id'] = self.avatar_selected_preset
        if self.avatar_selected_preset in v['cropper']['preset_urls']:
            v['url'] = v['cropper']['preset_urls'][self.avatar_selected_preset]
        return v

    avatar = FileImgDescriptor(relation_name='avatar_file_img',
                               file_decorator=lambda u, r, f: f.attr(
                                   name='%s_for_user_avatar_%s' % (f.name, u.id),
                                   parent_id=u.system_folder_file_id,
                                   root_folder_id=u.system_folder_file_id),
                               image_size=[300, 400],
                               min_size=[100, 100],
                               aspect_ratio=[0.5, 2.],
                               after_get=lambda u, r, v: u.get_avatar_preset(r, v),
                               before_set=lambda u, r, v: u.set_avatar_preset(r, v),
                               no_selection_url=utils.fileUrl(RECORD_IDS.FOLDER_AND_FILE.no_user_avatar()))

    def login(self):
        if self.email_confirmed and not self.banned:
            self.ping()
            login_user(self)
        return True

    @staticmethod
    def logout():
        logout_user()

    def get_avatar(self):
        return self.avatar

    email_conf_token = Column(TABLE_TYPES['token'])
    email_conf_tm = Column(TABLE_TYPES['timestamp'])
    pass_reset_token = Column(TABLE_TYPES['token'])
    pass_reset_conf_tm = Column(TABLE_TYPES['timestamp'])

    employments = relationship('UserCompany', back_populates='user')

    companies = relationship('Company', back_populates='user_owner')

    password = None
    password_confirmation = None
    password_hash = Column(TABLE_TYPES['string_128'], nullable=False)

    country_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('country.id'), nullable=True)
    country = relationship('Country')

    registered_via = Column(TABLE_TYPES['string_30'], nullable=False, default='email')

    google_id = Column(TABLE_TYPES['id_soc_net'])
    facebook_id = Column(TABLE_TYPES['id_soc_net'])
    linkedin_id = Column(TABLE_TYPES['id_soc_net'])
    twitter_id = Column(TABLE_TYPES['id_soc_net'])
    microsoft_id = Column(TABLE_TYPES['id_soc_net'])
    yahoo_id = Column(TABLE_TYPES['id_soc_net'])

    tos = Column(TABLE_TYPES['boolean'], default=False)


    def is_active(self, check_only_banned=None, raise_exception_redirect_if_not=False):
        if self.banned:
            if raise_exception_redirect_if_not:
                raise errors.NoRights(redirect_to=url_for('index.banned'))
            return "Sorry!You were baned! Please send a message to the administrator to know details!"
        if not check_only_banned and not self.tos:
            if raise_exception_redirect_if_not:
                raise errors.NoRights(redirect_to=url_for('index.welcome'))
            return "Sorry!You must confirm license first!"
        if not self.email_confirmed:
            if raise_exception_redirect_if_not:
                raise errors.NoRights(redirect_to=url_for('auth.email_confirmation'))
            return "Sorry!You must be confirmed!"
        return True

    def validate(self, is_new):

        ret = super().validate(is_new)
        if not re.match(r'[^\s]{2}', self.first_name):
            ret['errors']['first_name'] = 'Your First name must be at least 2 characters long.'
        if not re.match(r'[^\s]{2}', self.last_name):
            ret['errors']['last_name'] = 'Your Last name must be at least 2 characters long.'

        if not re.match(REGEXP.EMAIL, self.address_email):
            ret['errors']['email'] = 'Please enter correct email'
        elif is_new and db(User, address_email=self.address_email).first():
            ret['errors']['email'] = 'Sorry. this email is taken'

        if is_new and (self.password is None or self.password == ''):
            ret['errors']['password'] = 'Please provide password'

        if self.password is not None:
            if self.check_password_strength() < 30:
                ret['errors']['password'] = 'password is too weak'
            elif self.check_password_strength() < 50:
                ret['warnings']['password'] = 'password weak, but ok'

        if self.password is not None and self.password != self.password_confirmation:
            ret['errors']['password_confirmation'] = 'Password and confirmation does not match'

        return ret

    @staticmethod
    def user_query(user_id):
        ret = db(User, id=user_id).one()
        return ret

    def set_password_hash(self):
        if self.password is not None:
            self.password_hash = generate_password_hash(self.password,
                                                        method='pbkdf2:sha256',
                                                        salt_length=32)

    def ping(self):
        self.last_seen_tm = datetime.datetime.utcnow()
        g.db.add(self)
        g.db.commit()

    @staticmethod
    def get_unread_message_count(user_id, contact_id=None):
        return db_utils.execute_function("message_unread_count('%s', %s)" % (
            user_id, 'NULL' if contact_id is None else ("'" + contact_id + "'")))

    @staticmethod
    def get_unread_notification_count(user_id):
        return db_utils.execute_function("notification_unread_count('%s')" % (user_id,))

    @staticmethod
    def get_contact_request_count(user_id):
        return db_utils.execute_function("contact_request_count('%s')" % (user_id,))

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = '//secure.gravatar.com/avatar'
        else:
            url = '//www.gravatar.com/avatar'

        email = getattr(self, 'address_email', 'guest@' + Config.MAIN_DOMAIN)
        hash = hashlib.md5(email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    # def logged_in_via(self):
    #     via = None
    #     if self.address_email:
    #         via = REGISTERED_WITH_FLIPPED['profireader']
    #     else:
    #         short_soc_net = SOCIAL_NETWORKS[1:]
    #         for soc_net in short_soc_net:
    #             x = soc_net + '_id'
    #             if getattr(self, x):
    #                 via = REGISTERED_WITH_FLIPPED[soc_net]
    #                 break
    #     return via
    #
    #
    # def attribute_getter(self, logged_via, attr):
    #     if logged_via == 'profireader' and attr == 'id':
    #         full_attr = 'id'
    #     else:
    #         full_attr = logged_via + '_' + attr
    #     attr_value = getattr(self, full_attr)
    #     return attr_value

    def verify_password(self, password):
        return self.password_hash and \
               check_password_hash(self.password_hash, password)

    def check_password_strength(self):
        return len(self.password) * 10

    def generate_confirmation_token(self, addtourl):
        self.email_conf_token = random.getrandbits(128)
        self.email_conf_tm = datetime.datetime.now()

        email_utils.send_email(subject='Confirm Your Account',
                               html=render_template('auth/email/resend_confirmation.html', user=self,
                                                    confirmation_url=url_for('auth.email_confirmation',
                                                                             token=self.email_conf_token,
                                                                             _external=True, **addtourl)
                                                    ),
                               send_to=[self.address_email])

        return self

    def confirm_email(self):
        if self.email_conf_tm.timestamp() > int(time.time()) - current_app.config.get('EMAIL_CONFIRMATION_TOKEN_TTL',
                                                                                      3600 * 24):
            self.email_confirmed = True
            self.email_conf_token = None
        return self.email_confirmed

    def generate_pass_reset_token(self):
        self.pass_reset_token = random.getrandbits(128)
        self.pass_reset_conf_tm = datetime.datetime.now()

        email_utils.send_email(subject='Reset password',
                               html=render_template('auth/email/reset_password.html', user=self,
                                                    reset_password_url=url_for('auth.reset_password',
                                                                               token=self.pass_reset_token,
                                                                               _external=True)
                                                    ),
                               send_to=[self.address_email])

        return self

    def reset_password(self):
        self.pass_reset_token = None
        self.set_password_hash()
        self.email_confirmed = True
        self.email_conf_token = None
        g.db.add(self)
        g.db.commit()
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(address_email=new_email).first() \
                is not None:
            return False
        self.address_email = new_email
        return True


    def get_client_side_dict(self,
                             fields='id|full_name'
                                    '|address_email|first_name|last_name|address_url'
                                    '|address_phone|address_location|address_city|gender|lang|about|country_id|tos|address_phone'
                                    '|birth_tm',
                             more_fields=None):
        return self.to_dict(fields, more_fields)


class Group(Base, PRBase):
    __tablename__ = 'group'
    id = Column(TABLE_TYPES['string_30'], primary_key=True)


    # profireader_(name|first_name|last_name|email|gender|phone|link)
