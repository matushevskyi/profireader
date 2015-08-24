from flask import request, current_app
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column, ForeignKey, event
from sqlalchemy.orm import relationship
from os import urandom
from db_init import Base, db_session
from sqlalchemy.orm import validates


from ..constants.TABLE_TYPES import TABLE_TYPES
from ..constants.SOCIAL_NETWORKS import SOCIAL_NETWORKS, SOC_NET_NONE
from ..constants.USER_REGISTERED import REGISTERED_WITH_FLIPPED, \
    REGISTERED_WITH
from ..constants.PROFILE_NECESSARY_FIELDS import PROFILE_NECESSARY_FIELDS
from flask.ext.login import UserMixin
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer

from sqlalchemy import String
import hashlib
from flask.ext.login import UserMixin, AnonymousUserMixin



class PRColumn(Column):

    regexp = None;

    def __init__(self, *args, **kwargs):

        if 'regexp' in kwargs:
            self.regexp = kwargs.pop('regexp');

        super(PRColumn, self).__init__(*args, **kwargs)

        #
        #
        # def validate_address(self, key, address):
        #     assert '@' in address.email
        #     return address




class PRBase(Base):

    errors = {}
    warnings = {}
    notices = {}

    def __init__(self, *args, **kwargs):


        @validates('addresses', include_backrefs=False)

        def validate_address(self, key, address):
            assert '@' in address.email
            return address

        super(Base, self).__init__(*args, **kwargs)

class User(PRBase, UserMixin):
    __tablename__ = 'user'

    # PROFIREADER REGISTRATION DATA
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)

    @validates('addresses', include_backrefs=False)
    def validate_address(self, key, address):
        assert '@' in address.email
        return address

    personal_folder_file_id = Column(String(36), ForeignKey('file.id'))
    profireader_email = Column(TABLE_TYPES['email'], unique=True)
    profireader_first_name = Column(TABLE_TYPES['name'])
    profireader_last_name = Column(TABLE_TYPES['name'])
    profireader_name = Column(TABLE_TYPES['name'])
    profireader_gender = Column(TABLE_TYPES['gender'])
    profireader_link = Column(TABLE_TYPES['link'])


    profireader_phone = Column(TABLE_TYPES['phone'])
    profireader_avatar_file_id = Column(String(36), ForeignKey('file.id'))
    user_right_in_company = relationship('UserCompany', backref='user')
    about_me = Column(TABLE_TYPES['text'])
    location = Column(TABLE_TYPES['location'])
    companies = relationship('Company', backref='users')
    # SECURITY DATA

    password_hash = Column(TABLE_TYPES['password_hash'])
    confirmed = Column(TABLE_TYPES['boolean'], default=False)

    registered_tm = Column(TABLE_TYPES['timestamp'],
                           default=datetime.datetime.utcnow)
    last_seen = Column(TABLE_TYPES['timestamp'],
                       default=datetime.datetime.utcnow)
    avatar_hash = Column(TABLE_TYPES['avatar_hash'])

    #status_id = Column(Integer, db.ForeignKey('status.id'))

    email_conf_token = Column(TABLE_TYPES['token'])
    email_conf_tm = Column(TABLE_TYPES['timestamp'])
    pass_reset_token = Column(TABLE_TYPES['token'])
    pass_reset_conf_tm = Column(TABLE_TYPES['timestamp'])

    # registered_via = Column(_T['REGISTERED_VIA'])

# FB_NET_FIELD_NAMES = ['id', 'email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']
# SOCIAL_NETWORKS = ['profireader', 'google', 'facebook', 'linkedin', 'twitter', 'microsoft', 'yahoo']

    # GOOGLE
    google_id = Column(TABLE_TYPES['id_soc_net'])
    google_email = Column(TABLE_TYPES['email'], unique=True)
    google_first_name = Column(TABLE_TYPES['name'])
    google_last_name = Column(TABLE_TYPES['name'])
    google_name = Column(TABLE_TYPES['name'])
    google_gender = Column(TABLE_TYPES['gender'])
    google_link = Column(TABLE_TYPES['link'])
    google_phone = Column(TABLE_TYPES['phone'])

    # FACEBOOK
    facebook_id = Column(TABLE_TYPES['id_soc_net'])
    facebook_email = Column(TABLE_TYPES['email'], unique=True)
    facebook_first_name = Column(TABLE_TYPES['name'])
    facebook_last_name = Column(TABLE_TYPES['name'])
    facebook_name = Column(TABLE_TYPES['name'])
    facebook_gender = Column(TABLE_TYPES['gender'])
    facebook_link = Column(TABLE_TYPES['link'])
    facebook_phone = Column(TABLE_TYPES['phone'])

    # LINKEDIN
    linkedin_id = Column(TABLE_TYPES['id_soc_net'])
    linkedin_email = Column(TABLE_TYPES['email'], unique=True)
    linkedin_first_name = Column(TABLE_TYPES['name'])
    linkedin_last_name = Column(TABLE_TYPES['name'])
    linkedin_name = Column(TABLE_TYPES['name'])
    linkedin_gender = Column(TABLE_TYPES['gender'])
    linkedin_link = Column(TABLE_TYPES['link'])
    linkedin_phone = Column(TABLE_TYPES['phone'])

    # TWITTER
    twitter_id = Column(TABLE_TYPES['id_soc_net'])
    twitter_email = Column(TABLE_TYPES['email'], unique=True)
    twitter_first_name = Column(TABLE_TYPES['name'])
    twitter_last_name = Column(TABLE_TYPES['name'])
    twitter_name = Column(TABLE_TYPES['name'])
    twitter_gender = Column(TABLE_TYPES['gender'])
    twitter_link = Column(TABLE_TYPES['link'])
    twitter_phone = Column(TABLE_TYPES['phone'])

    # MICROSOFT
    microsoft_id = Column(TABLE_TYPES['id_soc_net'])
    microsoft_email = Column(TABLE_TYPES['email'], unique=True)
    microsoft_first_name = Column(TABLE_TYPES['name'])
    microsoft_last_name = Column(TABLE_TYPES['name'])
    microsoft_name = Column(TABLE_TYPES['name'])
    microsoft_gender = Column(TABLE_TYPES['gender'])
    microsoft_link = Column(TABLE_TYPES['link'])
    microsoft_phone = Column(TABLE_TYPES['phone'])

    # YAHOO
    yahoo_id = Column(TABLE_TYPES['id_soc_net'])
    yahoo_email = Column(TABLE_TYPES['email'], unique=True)
    yahoo_first_name = Column(TABLE_TYPES['name'])
    yahoo_last_name = Column(TABLE_TYPES['name'])
    yahoo_name = Column(TABLE_TYPES['name'])
    yahoo_gender = Column(TABLE_TYPES['gender'])
    yahoo_link = Column(TABLE_TYPES['link'])
    yahoo_phone = Column(TABLE_TYPES['phone'])

    def __init__(self,
                 companies=[],
                 fk_user_right_in_company=None,
                 user_right_in_company=[],
                 PROFIREADER_ALL=SOC_NET_NONE['profireader'],
                 GOOGLE_ALL=SOC_NET_NONE['google'],
                 FACEBOOK_ALL=SOC_NET_NONE['facebook'],
                 LINKEDIN_ALL=SOC_NET_NONE['linkedin'],
                 TWITTER_ALL=SOC_NET_NONE['twitter'],
                 MICROSOFT_ALL=SOC_NET_NONE['microsoft'],
                 YAHOO_ALL=SOC_NET_NONE['yahoo'],

                 location=None,
                 about_me=None,
                 #password=None,
                 confirmed=False,

                 email_conf_key=None,
                 email_conf_tm=None,
                 pass_reset_key=None,
                 pass_reset_conf_tm=None,
                 ):
        self.companies = companies
        self.fk_user_right_in_company = fk_user_right_in_company
        self.user_right_in_company = user_right_in_company
        self.profireader_email = PROFIREADER_ALL['email']
        self.profireader_first_name = PROFIREADER_ALL['first_name']
        self.profireader_last_name = PROFIREADER_ALL['last_name']
        self.profireader_name = PROFIREADER_ALL['name']
        self.profireader_gender = PROFIREADER_ALL['gender']
        self.profireader_link = PROFIREADER_ALL['link']
        self.profireader_phone = PROFIREADER_ALL['phone']

        self.about_me = about_me
        self.location = location
        #self.password = password
        self.confirmed = confirmed

        self.registered_tm = datetime.datetime.utcnow()   # here problems are possible

        self.email_conf_key = email_conf_key
        self.email_conf_tm = email_conf_tm
        self.pass_reset_key = pass_reset_key
        self.pass_reset_conf_tm = pass_reset_conf_tm

# FB_NET_FIELD_NAMES = ['id', 'email', 'first_name', 'last_name', 'name', 'gender', 'link', 'phone']

        self.google_id = GOOGLE_ALL['id']
        self.google_email = GOOGLE_ALL['email']
        self.google_first_name = GOOGLE_ALL['first_name']
        self.google_last_name = GOOGLE_ALL['last_name']
        self.google_name = GOOGLE_ALL['name']
        self.google_gender = GOOGLE_ALL['gender']
        self.google_link = GOOGLE_ALL['link']
        self.google_phone = GOOGLE_ALL['phone']

        self.facebook_id = FACEBOOK_ALL['id']
        self.facebook_email = FACEBOOK_ALL['email']
        self.facebook_first_name = FACEBOOK_ALL['first_name']
        self.facebook_last_name = FACEBOOK_ALL['last_name']
        self.facebook_name = FACEBOOK_ALL['name']
        self.facebook_gender = FACEBOOK_ALL['gender']
        self.facebook_link = FACEBOOK_ALL['link']
        self.facebook_phone = FACEBOOK_ALL['phone']

        self.linkedin_id = LINKEDIN_ALL['id']
        self.linkedin_email = LINKEDIN_ALL['email']
        self.linkedin_first_name = LINKEDIN_ALL['first_name']
        self.linkedin_last_name = LINKEDIN_ALL['last_name']
        self.linkedin_name = LINKEDIN_ALL['name']
        self.linkedin_gender = LINKEDIN_ALL['gender']
        self.linkedin_link = LINKEDIN_ALL['link']
        self.linkedin_phone = LINKEDIN_ALL['phone']

        self.twitter_id = TWITTER_ALL['id']
        self.twitter_email = TWITTER_ALL['email']
        self.twitter_first_name = TWITTER_ALL['first_name']
        self.twitter_last_name = TWITTER_ALL['last_name']
        self.twitter_name = TWITTER_ALL['name']
        self.twitter_gender = TWITTER_ALL['gender']
        self.twitter_link = TWITTER_ALL['link']
        self.twitter_phone = TWITTER_ALL['phone']

        self.microsoft_id = MICROSOFT_ALL['id']
        self.microsoft_email = MICROSOFT_ALL['email']
        self.microsoft_first_name = MICROSOFT_ALL['first_name']
        self.microsoft_last_name = MICROSOFT_ALL['last_name']
        self.microsoft_name = MICROSOFT_ALL['name']
        self.microsoft_gender = MICROSOFT_ALL['gender']
        self.microsoft_link = MICROSOFT_ALL['link']
        self.microsoft_phone = MICROSOFT_ALL['phone']

        self.yahoo_id = YAHOO_ALL['id']
        self.yahoo_email = YAHOO_ALL['email']
        self.yahoo_first_name = YAHOO_ALL['first_name']
        self.yahoo_last_name = YAHOO_ALL['last_name']
        self.yahoo_name = YAHOO_ALL['name']
        self.yahoo_gender = YAHOO_ALL['gender']
        self.yahoo_link = YAHOO_ALL['link']
        self.yahoo_phone = YAHOO_ALL['phone']

    def ping(self):
        self.last_seen = datetime.datetime.utcnow()
        db_session.add(self)
        db_session.commit()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'

        email = 'guest@profireader.com'
        if self.profireader_email:
            email = self.profireader_email

        hash = self.avatar_hash or hashlib.md5(
            email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def profile_completed(self):
        completeness = True
        for field in PROFILE_NECESSARY_FIELDS:
            if not getattr(self, field):
                completeness = False
                break
        #self.completeness = completeness
        #db_session.add(self)
        #db_session.commit()
        return completeness

    def logged_in_via(self):
        via = None
        if self.profireader_email:
            via = REGISTERED_WITH_FLIPPED['profireader']
        else:
            short_soc_net = SOCIAL_NETWORKS[1:]
            for soc_net in short_soc_net:
                x = soc_net+'_id'
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
    #@property
    def attribute_getter(self, logged_via, attr):
        if logged_via == 'profireader' and attr == 'id':
            full_attr = 'id'
        else:
            full_attr = logged_via + '_' + attr
        attr_value = getattr(self, full_attr)
        return attr_value

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')


    # we use SHA256.
    # https://crackstation.net/hashing-security.htm
    # "the output of SHA256 is 256 bits (32 bytes), so the salt should be at least 32 random bytes."
    #
    # another (simplier) approach can be user here.
    # see: http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.password
    # https://pythonhosted.org/passlib/lib/passlib.context-tutorial.html#full-integration-example
    @password.setter
    def password(self, password):
        self.password_hash = \
            generate_password_hash(password,
                                   method='pbkdf2:sha256',
                                   salt_length=32)  # salt_length=8

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        #with app.app_context
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db_session.add(self)
        db_session.commit()
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db_session.add(self)
        db_session.commit()
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
        if self.query.filter_by(profireader_email=new_email).first() \
                is not None:
            return False
        self.profireader_email = new_email
        return True

    def __repr__(self):
        return "<User(id = %r)>" % self.id



@event.listens_for(User, 'init')
def validate_new_object(target, args, kwargs):
    errors = {}
    varnings = {}
    noteces = {}
    if target.email:
        errors['email']= 'wrong email'
    if target.password:
        errors['password'] = 'wrong email'
    if target.password2 != target.password:
        errors['password2'] = 'password confirmation mismatch'
    print(target)
    print(args)
    print(kwargs)

