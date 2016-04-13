from ..models.pr_base import Base, PRBase
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from utils.db_utils import db

class Country(Base, PRBase):
    __tablename__ = 'country'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    iso = Column(TABLE_TYPES['iso'])
    name = Column(TABLE_TYPES['name'])
    phonecode = Column(TABLE_TYPES['phonecode'])

    @staticmethod
    def get_countries():
        return [{'id': country.id, 'name': country.name} for country in db(Country).all()]