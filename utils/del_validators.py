# see: http://stackoverflow.com/questions/8980735/how-can-i-verify-column-data-types-in-the-sqlalchemy-orm
# see: http://docs.sqlalchemy.org/en/rel_0_9/orm/mapped_attributes.html
# see: http://stackoverflow.com/questions/2390753/is-there-a-way-to-transparently-perform-validation-on-sqlalchemy-objects
#
# I don't understand the statement:
# Validators, like all attribute extensions, are only called by normal
# userland code; they are not issued when the ORM is populating the object:


from sqlalchemy import Integer, String, DateTime
import datetime
import re

def validate_int(value):   # is it correct?
    if isinstance(value, str):
        value = int(value)
    else:
        assert isinstance(value, int)
    return value


def validate_string(value):
    assert (isinstance(value, str) or (value is None))
    return value


def validate_datetime(value):
    assert isinstance(value, datetime.datetime)
    return value


def validate_email(email):
    EMAIL_REGEX = re.compile(r'[^@]+@[^@]+\.[^@]+')
    assert EMAIL_REGEX.match(email) is True, '%s email is not valid' % email
    return email

validators = {
    Integer: validate_int,
    String: validate_string,
    DateTime: validate_datetime,
    #Email: validate_email
}
