from sqlalchemy import Integer, String, TIMESTAMP, SMALLINT, BOOLEAN, Column, ForeignKey, UnicodeText, BigInteger, Binary
from sqlalchemy_utils.types.phone_number import PhoneNumberType
from sqlalchemy_utils import URLType
# read this about UUID:
# http://stackoverflow.com/questions/183042/how-can-i-use-uuids-in-sqlalchemy
# http://stackoverflow.com/questions/20532531/how-to-set-a-column-default-to-a-postgresql-function-using-sqlalchemy
TABLE_TYPES = {
    'id_profireader': String(36),
    # 'file_column': Column(String(36), ForeignKey('file.id')),
    # 'id_column': Column(String(36), primary_key=True),
    # 'user_column': Column(String(36), ForeignKey('user.id'), nullable=False),
    # 'company_column': Column(String(36), ForeignKey('company.id'), nullable=False),


    'password_hash': String(128),  # String(128) SHA-256
    'token': String(128),
    'timestamp': TIMESTAMP,
    'id_soc_net': String(50),
    'role': String(36),
    'location': String(64),

    'boolean': BOOLEAN,
    'status': String(36),
    'rights': String(30),
    'bigint': BigInteger,

    # http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.phone_number
    'phone': PhoneNumberType(country_code='UA'),  # (country_code='UA')

    # http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.url
    # read also https://github.com/gruns/furl
    'link': URLType,  # user = User(website=u'www.example.com'),
    'email': String(100),
    'name': String(100),
    'text': UnicodeText(length=65535),
    'gender': String(6),
    'avatar_hash': String(32),
    'binary': Binary
}
#
#
# USER_TABLE_TYPES = {'id': id_profireader_type,
#                     'google_id': id_soc_net_type,
#                     'facebook_id': id_soc_net_type,
#                     'linkedin_id': id_soc_net_type,
#                     'twitter_id': id_soc_net_type,
#                     'microsoft_id': id_soc_net_type,
#                     'yahoo_id': id_soc_net_type,
#
#                     'email': email_type,
#                     'first_name':  String(300),
#                     'last_name': String(300),
#                     'name': String(601),
#                     'gender': String(10),
#                     'link': link_type,
#                     'phone': phone_type,
#
#                     'ABOUT_ME': String(6000),
#                     'PASSWORD_HASH': String(128),  # String(128) SHA-256
#
#                     'REGISTERED_ON': TIMESTAMP,
#
#                     'EMAIL_CONF_KEY': String(100),
#                     'EMAIL_CONF_TM': TIMESTAMP,
#                     'PASS_RESET_KEY': String(100),
#                     'PASS_RESET_CONF_TM': TIMESTAMP,
#                     'PROFILE_COMPLETED': BOOLEAN
#                     }

# USER_STATUS_TABLE_TYPES = {'id': SMALLINT, 'google_id': id_soc_net_type}
