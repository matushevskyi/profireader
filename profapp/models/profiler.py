from .pr_base import PRBase, Base
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from utils.db_utils import db


class Profiler(PRBase, Base):
    __tablename__ = 'func_profiler'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    name = Column(TABLE_TYPES['name'], nullable=False)
    blueprint_name = Column(TABLE_TYPES['name'], nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    total_time = Column(TABLE_TYPES['timestamp'])
    average_time = Column(TABLE_TYPES['timestamp'])
    method = Column(TABLE_TYPES['string_30'])
    total_using = Column(TABLE_TYPES['int'])

    def __init__(self, name=None,  blueprint_name=None, total_using=None, cr_tm=None, md_tm=None,
                 total_time=None, average_time=None, method=None):
        self.name = name
        self.blueprint_name = blueprint_name
        self.total_using = total_using
        self.cr_tm = cr_tm
        self.md_tm = md_tm
        self.total_time = total_time
        self.average_time = average_time
        self.method = method

    def update_profile(self, time, method):
        self.attr({
            'total_using': self.total_using+1,
            'total_time': self.total_time+time,
            'method': method

        }).save()



    def create_profile(self, name, blueprint_name, time, method):
        self.attr({
            'name': name,
            'blueprint_name':blueprint_name,
            'total_using': 1,
            'total_time': time,
            'average_time': time,
            'method': method

        }).save()

