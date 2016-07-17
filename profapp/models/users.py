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
from ..constants.USER_REGISTERED import REGISTERED_WITH_FLIPPED, \
    REGISTERED_WITH
# from ..constants.PROFILE_NECESSARY_FIELDS import PROFILE_NECESSARY_FIELDS
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from utils.db_utils import db
from sqlalchemy import String
from . import country
import hashlib
from flask.ext.login import UserMixin
from .files import File, FileImg
from .pr_base import PRBase, Base
from ..constants.SEARCH import RELEVANCE
# from ..utils import fileUrl
from .. import utils
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE

import random
import time
from .files import FileImg, FileImgDescriptor
from flask.ext.login import logout_user, current_user, login_user


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
                               no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_user_avatar()))

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

    # registered_via = Column(_T['REGISTERED_VIA'])
    # employers = relationship('Company', secondary='user_company',
    #                          backref=backref("employees", lazy='dynamic'))  # Correct

    employments = relationship('UserCompany', back_populates='user')

    companies = relationship('Company', back_populates='user_owner')

    password = ''
    password_confirmation = ''
    password_hash = Column(TABLE_TYPES['string_128'], nullable=False)

    # FB_NET_FIELD_NAMES = ['id', 'email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']
    # SOCIAL_NETWORKS = ['profireader', 'google', 'facebook', 'linkedin', 'twitter', 'microsoft', 'yahoo']
    country_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('country.id'), nullable=True)
    country = relationship('Country')

    # GOOGLE
    google_id = Column(TABLE_TYPES['id_soc_net'])
    # google_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # google_first_name = Column(TABLE_TYPES['name'])
    # google_last_name = Column(TABLE_TYPES['name'])
    # google_name = Column(TABLE_TYPES['name'])
    # google_gender = Column(TABLE_TYPES['gender'])
    # google_link = Column(TABLE_TYPES['link'])
    # google_phone = Column(TABLE_TYPES['phone'])

    # FACEBOOK
    facebook_id = Column(TABLE_TYPES['id_soc_net'])
    # facebook_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # facebook_first_name = Column(TABLE_TYPES['name'])
    # facebook_last_name = Column(TABLE_TYPES['name'])
    # facebook_name = Column(TABLE_TYPES['name'])
    # facebook_gender = Column(TABLE_TYPES['gender'])
    # facebook_link = Column(TABLE_TYPES['link'])
    # facebook_phone = Column(TABLE_TYPES['phone'])

    # LINKEDIN
    linkedin_id = Column(TABLE_TYPES['id_soc_net'])
    # linkedin_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # linkedin_first_name = Column(TABLE_TYPES['name'])
    # linkedin_last_name = Column(TABLE_TYPES['name'])
    # linkedin_name = Column(TABLE_TYPES['name'])
    # linkedin_gender = Column(TABLE_TYPES['gender'])
    # linkedin_link = Column(TABLE_TYPES['link'])
    # linkedin_phone = Column(TABLE_TYPES['phone'])

    # TWITTER
    twitter_id = Column(TABLE_TYPES['id_soc_net'])
    # twitter_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # twitter_first_name = Column(TABLE_TYPES['name'])
    # twitter_last_name = Column(TABLE_TYPES['name'])
    # twitter_name = Column(TABLE_TYPES['name'])
    # twitter_gender = Column(TABLE_TYPES['gender'])
    # twitter_link = Column(TABLE_TYPES['link'])
    # twitter_phone = Column(TABLE_TYPES['phone'])

    # MICROSOFT
    microsoft_id = Column(TABLE_TYPES['id_soc_net'])
    # microsoft_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # microsoft_first_name = Column(TABLE_TYPES['name'])
    # microsoft_last_name = Column(TABLE_TYPES['name'])
    # microsoft_name = Column(TABLE_TYPES['name'])
    # microsoft_gender = Column(TABLE_TYPES['gender'])
    # microsoft_link = Column(TABLE_TYPES['link'])
    # microsoft_phone = Column(TABLE_TYPES['phone'])


    # YAHOO
    yahoo_id = Column(TABLE_TYPES['id_soc_net'])

    # yahoo_email = Column(TABLE_TYPES['email'], unique=True, index=True)
    # yahoo_first_name = Column(TABLE_TYPES['name'])
    # yahoo_last_name = Column(TABLE_TYPES['name'])
    # yahoo_name = Column(TABLE_TYPES['name'])
    # yahoo_gender = Column(TABLE_TYPES['gender'])
    # yahoo_link = Column(TABLE_TYPES['link'])
    # yahoo_phone = Column(TABLE_TYPES['phone'])
    tos = Column(TABLE_TYPES['boolean'], default=False)

    # search_fields = {'full_name': {'relevance': lambda field='full_name': RELEVANCE.full_name},
    #                  'about_me': {'relevance': lambda field='about_me': RELEVANCE.about_me},
    #                  'address_email': {'relevance': lambda field='address_email': RELEVANCE.address_email}}

    # get all users in company : company.employees
    # get all users companies : user.employers

    # def __init__(self,
    #              # user_rights_in_profireader_def=[],
    #              # user_rights_in_profireader_undef=[],
    #              PROFIREADER_ALL=SOC_NET_NONE['profireader'],
    #              GOOGLE_ALL=SOC_NET_NONE['google'],
    #              FACEBOOK_ALL=SOC_NET_NONE['facebook'],
    #              LINKEDIN_ALL=SOC_NET_NONE['linkedin'],
    #              TWITTER_ALL=SOC_NET_NONE['twitter'],
    #              MICROSOFT_ALL=SOC_NET_NONE['microsoft'],
    #              YAHOO_ALL=SOC_NET_NONE['yahoo'],
    #
    #              location=None,
    #              about_me=None,
    #              password=None,
    #              confirmed=False,
    #              banned=False,
    #              lang=None,
    #
    #              email_conf_key=None,
    #              email_conf_tm=None,
    #              pass_reset_key=None,
    #              pass_reset_conf_tm=None,
    #              tos=None
    #              ):
    #
    #     self.address_email = PROFIREADER_ALL['email']
    #     self.first_name = PROFIREADER_ALL['first_name']
    #     self.last_name = PROFIREADER_ALL['last_name']
    #     self.full_name = PROFIREADER_ALL['name']
    #     self.gender = PROFIREADER_ALL['gender']
    #     self.address_url = PROFIREADER_ALL['link']
    #     self.address_phone = PROFIREADER_ALL['phone']
    #     self.tos = tos
    #     self.about_me = about_me
    #     self.location = location
    #     self.password = password
    #
    #     self.email_confirmed = confirmed
    #     self.banned = banned
    #     self.birth_tm = None
    #     self.registered_tm = datetime.datetime.utcnow()  # here problems are possible
    #     self.lang = lang
    #     self.email_conf_key = email_conf_key
    #     self.email_conf_tm = email_conf_tm
    #     self.pass_reset_key = pass_reset_key
    #     self.pass_reset_conf_tm = pass_reset_conf_tm
    #
    #     # FB_NET_FIELD_NAMES = ['id', 'email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']
    #
    #     self.google_id = GOOGLE_ALL['id']
    #     self.google_email = GOOGLE_ALL['email']
    #     self.google_first_name = GOOGLE_ALL['first_name']
    #     self.google_last_name = GOOGLE_ALL['last_name']
    #     self.google_name = GOOGLE_ALL['name']
    #     self.google_gender = GOOGLE_ALL['gender']
    #     self.google_link = GOOGLE_ALL['link']
    #     self.google_phone = GOOGLE_ALL['phone']
    #
    #     self.facebook_id = FACEBOOK_ALL['id']
    #     self.facebook_email = FACEBOOK_ALL['email']
    #     self.facebook_first_name = FACEBOOK_ALL['first_name']
    #     self.facebook_last_name = FACEBOOK_ALL['last_name']
    #     self.facebook_name = FACEBOOK_ALL['name']
    #     self.facebook_gender = FACEBOOK_ALL['gender']
    #     self.facebook_link = FACEBOOK_ALL['link']
    #     self.facebook_phone = FACEBOOK_ALL['phone']
    #
    #     self.linkedin_id = LINKEDIN_ALL['id']
    #     self.linkedin_email = LINKEDIN_ALL['email']
    #     self.linkedin_first_name = LINKEDIN_ALL['first_name']
    #     self.linkedin_last_name = LINKEDIN_ALL['last_name']
    #     self.linkedin_name = LINKEDIN_ALL['name']
    #     self.linkedin_gender = LINKEDIN_ALL['gender']
    #     self.linkedin_link = LINKEDIN_ALL['link']
    #     self.linkedin_phone = LINKEDIN_ALL['phone']
    #
    #     self.twitter_id = TWITTER_ALL['id']
    #     self.twitter_email = TWITTER_ALL['email']
    #     self.twitter_first_name = TWITTER_ALL['first_name']
    #     self.twitter_last_name = TWITTER_ALL['last_name']
    #     self.twitter_name = TWITTER_ALL['name']
    #     self.twitter_gender = TWITTER_ALL['gender']
    #     self.twitter_link = TWITTER_ALL['link']
    #     self.twitter_phone = TWITTER_ALL['phone']
    #
    #     self.microsoft_id = MICROSOFT_ALL['id']
    #     self.microsoft_email = MICROSOFT_ALL['email']
    #     self.microsoft_first_name = MICROSOFT_ALL['first_name']
    #     self.microsoft_last_name = MICROSOFT_ALL['last_name']
    #     self.microsoft_name = MICROSOFT_ALL['name']
    #     self.microsoft_gender = MICROSOFT_ALL['gender']
    #     self.microsoft_link = MICROSOFT_ALL['link']
    #     self.microsoft_phone = MICROSOFT_ALL['phone']
    #
    #     self.yahoo_id = YAHOO_ALL['id']
    #     self.yahoo_email = YAHOO_ALL['email']
    #     self.yahoo_first_name = YAHOO_ALL['first_name']
    #     self.yahoo_last_name = YAHOO_ALL['last_name']
    #     self.yahoo_name = YAHOO_ALL['name']
    #     self.yahoo_gender = YAHOO_ALL['gender']
    #     self.yahoo_link = YAHOO_ALL['link']
    #     self.yahoo_phone = YAHOO_ALL['phone']

    def is_active(self, check_only_banned=None, raise_exception_redirect_if_not = False):
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

        if self.password == '':
            self.password = None

        if is_new and not self.password:
            ret['errors']['password'] = 'Please provide password'

        if self.password and self.password != self.password_confirmation:
            ret['errors']['password_confirmation'] = 'Password and confirmation does not match'

        return ret

    @staticmethod
    def user_query(user_id):
        ret = db(User, id=user_id).one()
        return ret

    def set_password_hash(self):
        if self.password and self.password != '':
            self.password_hash = generate_password_hash(self.password,
                                                        method='pbkdf2:sha256',
                                                        salt_length=32)

    def ping(self):
        self.last_seen_tm = datetime.datetime.utcnow()
        g.db.add(self)
        g.db.commit()

    # def get_avatar(self, avatar_via, size=500, small_size=100, url=None):
    #     if avatar_via == 'upload':
    #         return self
    #     avatar_urls = dict(facebook=lambda s: 'http://graph.facebook.com/{facebook_id}/picture?width={size}&'
    #                                           'height={size}&redirect=0'.format(facebook_id=self.facebook_id, size=s),
    #                        google=lambda s: 'https://www.googleapis.com/plus/v1/people/{google_id}?'
    #                                         'fields=image&key={key}'.format(google_id=self.google_id,
    #                                                                         size=s, key=Config.GOOGLE_API_KEY_SIMPLE),
    #                        linkedin=lambda s, u=url: u if u else self.gravatar(size=s),
    #                        # vkontakte=lambda s, u=url: u if u else self.gravatar(size=s),
    #                        gravatar=lambda s: self.gravatar(size=s),
    #                        microsoft=lambda _: 'https://apis.live.net/v5.0/{microsoft_id}/picture'.format(
    #                            microsoft_id=self.microsoft_id))
    #     url = avatar_urls[avatar_via](size)
    #     url_small = avatar_urls[avatar_via](small_size)
    #     if avatar_via == 'facebook':
    #         avatar = json.load(req.urlopen(url=url))
    #         avatar_small = json.load(req.urlopen(url=url_small))
    #         if avatar['data'].get('is_silhouette'):
    #             self.profireader_avatar_url = self.gravatar(size=size)
    #             self.profireader_small_avatar_url = self.gravatar(size=small_size)
    #         else:
    #             self.profireader_avatar_url = avatar['data'].get('url')
    #             self.profireader_small_avatar_url = avatar_small['data'].get('url')
    #     elif avatar_via == 'google':
    #         avatar = json.load(req.urlopen(url=url))
    #         avatar_small = json.load(req.urlopen(url=url_small))
    #         if avatar['image'].get('isDefault'):
    #             self.profireader_avatar_url = self.gravatar(size=size)
    #             self.profireader_small_avatar_url = self.gravatar(size=small_size)
    #         else:
    #             self.profireader_avatar_url = avatar['image'].get('url')
    #             self.profireader_small_avatar_url = avatar_small['image'].get('url')
    #     elif avatar_via == 'linkedin':
    #         self.profireader_avatar_url = url
    #         self.profireader_small_avatar_url = url
    #     # elif avatar_via == 'vkontakte':
    #     #     avatar = json.load(urllib.urlopen("https://api.vk.com/method/users.get?v=5.8&fields="
    #     #                                 "photo_{size}&access_token={access_token}".
    #     #                                 format(size=str(size),
    #     #                                      access_token=access_token)))['response'][0].get(# Here needs right token from VK
    #     #                                         'photo_{size}'.format(size=size))
    #     #     avatar_small = json.load(urllib.urlopen("https://api.vk.com/method/users.get?v=5.8&fields="
    #     #                                       "photo_{size}&access_token={access_token}".
    #     #                                       format(size=str(small_size),
    #     #                                              access_token=access_token)))['response'][0].get(# Here needs right token from VK
    #     #                                              'photo_{size}'.format(size=small_size))
    #     #     self.profireader_avatar_url = url
    #     #     self.profireader_small_avatar_url = url
    #     elif avatar_via == 'microsoft':
    #         avatar = req.urlopen(url=url)
    #         if 'Default' not in avatar.url:
    #             self.profireader_avatar_url = avatar.url
    #             self.profireader_small_avatar_url = avatar.url
    #         else:
    #             self.profireader_avatar_url = self.gravatar(size=size)
    #             self.profireader_small_avatar_url = self.gravatar(size=small_size)
    #     elif avatar_via == 'gravatar':
    #         self.profireader_avatar_url = url
    #         self.profireader_small_avatar_url = url_small
    #
    #     return self

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = '//secure.gravatar.com/avatar'
        else:
            url = '//www.gravatar.com/avatar'

        email = getattr(self, 'address_email', 'guest@' + Config.MAIN_DOMAIN)
        hash = hashlib.md5(email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    # def set_avatar_client_side_dict(self, client_data):
    #     if client_data['selected_by_user']['type'] == 'preset':
    #         client_data['selected_by_user']['type'] = 'none'
    #         if client_data['selected_by_user']['class'] == 'glyphicon-share':
    #             self.profireader_avatar_url = self.gravatar(size=500)
    #             self.profireader_small_avatar_url = self.gravatar(size=100)
    #         else:
    #             raise ValueError("passed unknow preset class `{}`".format(client_data['selected_by_user']['class']))
    #
    #
    #     self.avatar_file_id = self.set_image_cropped_file(self.logo_file_properties(),
    #                                                       client_data, self.avatar_file_id, self.system_folder_file_id)
    #     if self.avatar_file_id:
    #         self.profireader_avatar_url = fileUrl(self.avatar_file_id)
    #         self.profireader_small_avatar_url = fileUrl(File.get(self.avatar_file_id).get_thumbnails((133,100)).id)
    #
    #     return self
    #
    # def get_avatar_client_side_dict(self):
    #     ret = self.get_image_cropped_file(self.logo_file_properties(),
    #                                       db(FileImg, croped_image_id=self.avatar_file_id).first())
    #
    #     if self.profireader_avatar_url == self.gravatar(size=500):
    #         ret['selected_by_user'] = {'type': 'preset', 'class': 'glyphicon-share'}
    #     return ret

    # def profile_completed(self):
    #     completeness = True
    #     # for field in PROFILE_NECESSARY_FIELDS:
    #     #     if not getattr(self, field):
    #     #         completeness = False
    #     #         break
    #     # self.completeness = completeness
    #     # g.db.add(self)
    #     # g.db.commit()
    #     return completeness

    def logged_in_via(self):
        via = None
        if self.address_email:
            via = REGISTERED_WITH_FLIPPED['profireader']
        else:
            short_soc_net = SOCIAL_NETWORKS[1:]
            for soc_net in short_soc_net:
                x = soc_net + '_id'
                if getattr(self, x):
                    via = REGISTERED_WITH_FLIPPED[soc_net]
                    break
        return via

    @property
    def phone_number(self):
        via = self.logged_in_via()
        phone = getattr(self, REGISTERED_WITH[via] + '_phone')
        return phone

    @property
    def show_email(self):
        via = self.logged_in_via()
        email = getattr(self, REGISTERED_WITH[via] + '_email')
        return email

    @property
    def user_name(self):
        via = self.logged_in_via()
        name = getattr(self, REGISTERED_WITH[via] + '_name')
        return name

    # attr below is one of the
    # ['email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']
    # @property
    def attribute_getter(self, logged_via, attr):
        if logged_via == 'profireader' and attr == 'id':
            full_attr = 'id'
        else:
            full_attr = logged_via + '_' + attr
        attr_value = getattr(self, full_attr)
        return attr_value


    # we use SHA256.
    # https://crackstation.net/hashing-security.htm
    # "the output of SHA256 is 256 bits (32 bytes), so the salt should be at least 32 random bytes."
    #
    # another (simplier) approach can be user here.
    # see: http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.password
    # https://pythonhosted.org/passlib/lib/passlib.context-tutorial.html#full-integration-example
    # @password.setter
    # def password(self, password):
    #     self.password_hash = None
    #     if password:
    #         self.password_hash = \
    #             generate_password_hash(password,
    #                                    method='pbkdf2:sha256',
    #                                    salt_length=32)  # salt_length=8

    def verify_password(self, password):
        return self.password_hash and \
               check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, addtourl):
        from flask import url_for, render_template
        from utils.pr_email import SendEmail

        self.email_conf_token = random.getrandbits(128)
        self.email_conf_tm = datetime.datetime.now()

        SendEmail().send_email(subject='Confirm Your Account',
                               html=render_template('auth/email/resend_confirmation.html', user=self,
                                                    confirmation_url=url_for('auth.email_confirmation',
                                                                             token=self.email_conf_token,
                                                                             _external=True, **addtourl)
                                                    ),
                               send_to=(self.address_email,))

        return self

    def confirm_email(self):
        if self.email_conf_tm.timestamp() > int(time.time()) - current_app.config.get('EMAIL_CONFIRMATION_TOKEN_TTL',
                                                                                      3600 * 24):
            self.email_confirmed = True
        return self.email_confirmed

    def generate_pass_reset_token(self):
        self.pass_reset_token = random.getrandbits(128)
        self.pass_reset_conf_tm = datetime.datetime.now()
        # if self.pass_reset_conf_tm.timestamp() > int(time.time()) - current_app.config.get('PASSWORD_CONFIRMATION_TOKEN_TTL', 3600*24):
        #     self.email_confirmed = True
        #     return self.email_confirmed
        return self

    def generate_reset_token(self):
        self.email_conf_token = random.getrandbits(128)
        if self.pass_reset_conf_tm.timestamp() > int(time.time()) - current_app.config.get(
                'PASSWORD_CONFIRMATION_TOKEN_TTL', 3600 * 24):
            self.email_confirmed = True
            return self.email_confirmed
        return self

    def reset_password(self, new_password):
        self.pass_reset_token = None
        self.password = new_password
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

    # def can(self, permissions):
    #     return self.role is not None and \
    #         (self.role.permissions & permissions) == permissions

    # def is_administrator(self):
    #    return self.can(Permission.ADMINISTER)

    def get_client_side_dict(self,
                             fields='id|full_name'
                                    '|address_email|first_name|last_name|address_url'
                                    '|address_phone|address_location|gender|lang|about|country_id|tos|address_phone'
                                    '|birth_tm',
                             more_fields=None):
        return self.to_dict(fields, more_fields)


class Group(Base, PRBase):
    __tablename__ = 'group'
    id = Column(TABLE_TYPES['string_30'], primary_key=True)


    # profireader_(name|first_name|last_name|email|gender|phone|link)
