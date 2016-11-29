from ..models.pr_base import Base, PRBase
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from tools.db_utils import db

class Country(Base, PRBase):
    __tablename__ = 'country'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    iso = Column(TABLE_TYPES['iso'])
    name = Column(TABLE_TYPES['name'])
    phonecode = Column(TABLE_TYPES['phonecode'])

    @staticmethod
    def get_countries():
        return [{'id': country.id, 'name': country.name} for country in db(Country).all()]

class Currency(Base, PRBase):
    __tablename__ = 'currency'
    id = Column(TABLE_TYPES['string_10'], primary_key=True)
    name = Column(TABLE_TYPES['string_100'])
    position = Column(TABLE_TYPES['int'])
    active = Column(TABLE_TYPES['boolean'])

    def get_client_side_dict(self, fields='id,name', more_fields=None):
        return self.to_dict(fields, more_fields)
