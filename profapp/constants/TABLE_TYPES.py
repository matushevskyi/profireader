from sqlalchemy import Integer, String, TIMESTAMP, SMALLINT, BOOLEAN, Column, ForeignKey, UnicodeText, BigInteger, \
    Binary, Float, Date
from sqlalchemy.dialects.postgresql import BIGINT, INTEGER, JSON, NUMERIC, INTERVAL
from profapp.models.permissions import BinaryRightsMetaClass

class RIGHTS(BIGINT):
    _rights_class = None

    def __init__(self, rights):
        if isinstance(rights, BinaryRightsMetaClass):
            self._rights_class = rights
        else:
            raise Exception(
                'rights attribute should be BinaryRights class')

        super(RIGHTS, self).__init__()

    def result_processor(self, dialect, coltype):
        def process(value):
            ret = self._rights_class._todict(value)
            return ret

        return process

    def bind_processor(self, dialect):
        def process(array):
            return self._rights_class._tobin(array)

        return process

    def adapt(self, impltype):
        return RIGHTS(self._rights_class)


# read this about UUID:
# http://stackoverflow.com/questions/183042/how-can-i-use-uuids-in-sqlalchemy
# http://stackoverflow.com/questions/20532531/how-to-set-a-column-default-to-a-postgresql-function-using-sqlalchemy
TABLE_TYPES = {
    'binary_rights': RIGHTS,
    # 'image': IMAGE,
    'date': Date,

    'id_profireader': String(36),

    'string_128': String(128),  # String(128) SHA-256
    'token': String(128),
    'timestamp': TIMESTAMP,
    'id_soc_net': String(50),
    'role': String(36),
    'location': String(64),

    'boolean': BOOLEAN,
    'status': String(36),
    'rights': String(40),
    'bigint': BIGINT,
    'int': INTEGER,
    'position': INTEGER,
    'float': Float,

    # http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.phone_number
    # 'phone': PhoneNumberType(country_code='UA'),  # (country_code='UA')
    'phone': String(50),  # (country_code='UA')

    # http://sqlalchemy-utils.readthedocs.org/en/latest/data_types.html#module-sqlalchemy_utils.types.url
    # read also https://github.com/gruns/furl
    # 'link': URLType,  # user = User(website=u'www.example.com'),
    'link': String(100),  # user = User(website=u'www.example.com'),
    'email': String(100),
    'name': String(200),
    'subtitle': String(1000),
    'string_10': String(10),
    'string_30': String(30),
    'string_100': String(100),
    'string_200': String(200),
    'string_500': String(500),
    'string_1000': String(1000),
    'string_10000': String(10000),
    'string_65535': String(65535),
    'short_name': String(50),
    'title': String(100),
    'short_text': String(120),
    'keywords': String(1000),
    'credentials': String(1000),
    'text': UnicodeText(length=65535),
    'gender': String(6),
    'language': String(3),
    'iso': String(2),
    'iso3': String(3),
    'numcode': String(6),
    'phonecode': String(5),
    'url': String(1000),  # URLType,
    'binary': Binary,
    'json': JSON,
    'price': NUMERIC(20, 2),
    'timeinterval': String(50),
}
