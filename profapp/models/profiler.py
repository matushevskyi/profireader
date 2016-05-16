from .pr_base import PRBase, Base
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from utils.db_utils import db


class Profiler(PRBase, Base):
    __tablename__ = 'func_profiler'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    name = Column(TABLE_TYPES['name'], nullable=False)
    blueprint_name = Column(TABLE_TYPES['name'], nullable=False)
    count_of_using = Column(TABLE_TYPES['int'])
    cr_tm = Column(TABLE_TYPES['timestamp'])
    last_use = Column(TABLE_TYPES['timestamp'])
    total_time_use_func = Column(TABLE_TYPES['timestamp'])
    average_time = Column(TABLE_TYPES['timestamp'])

    def __init__(self, name=None,  blueprint_name=None, count_of_using=None, cr_tm=None, last_use=None,
                 total_time=None, average_time=None):
        self.name = name
        self.blueprint_name = blueprint_name
        self.count_of_using = count_of_using
        self.cr_tm = cr_tm
        self.last_use = last_use
        self.total_time = total_time
        self.average_time = average_time



    def get_all_func(self):
        print(self)
        # return db(Profiler).all()
