from sqlalchemy import Column
from ..constants.TABLE_TYPES import TABLE_TYPES
from .pr_base import PRBase, Base
from tools.db_utils import db

class Config(Base, PRBase):
    __tablename__ = 'config'
    id = Column(TABLE_TYPES['name'], primary_key=True, nullable=False)
    value = Column(TABLE_TYPES['text'])
    type = Column(TABLE_TYPES['name'])
    comment = Column(TABLE_TYPES['text'])
    client_side = Column(TABLE_TYPES['boolean'])
    server_side = Column(TABLE_TYPES['boolean'])

    def __init__(self, id=None, value=None, type=None, comment=None, client_side=None, server_side=None):
        self.id = id
        self.value = value
        self.type = type
        self.comment = comment
        self.client_side = client_side
        self.server_side = server_side


    @staticmethod
    def subquery_search(template=None, url=None, **kwargs):
        sub_query = db(Config)
        if 'filter' in kwargs:
            if 'url' in kwargs['filter']:
                sub_query = sub_query.filter_by(url=kwargs['filter']['url'])
            if 'template' in kwargs['filter']:
                sub_query = sub_query.filter_by(template=kwargs['filter']['template'])
        if 'search_text' in kwargs:
            if 'name' in kwargs['search_text']:
                sub_query = sub_query.filter(Config.name.ilike("%" + kwargs['search_text']['name'] + "%"))
            if 'uk' in kwargs['search_text']:
                sub_query = sub_query.filter(Config.uk.ilike("%" + kwargs['search_text']['uk'] + "%"))
            if 'en' in kwargs['search_text']:
                sub_query = sub_query.filter(Config.en.ilike("%" + kwargs['search_text']['en'] + "%"))
        if 'cr_tm' in kwargs['sort']:
            sub_query = sub_query.order_by(Config.cr_tm.asc()) if kwargs['sort']['cr_tm'] == 'asc' else sub_query.order_by(TranslateTemplate.cr_tm.desc())
        elif 'ac_tm' in kwargs['sort']:
            sub_query = sub_query.order_by(Config.ac_tm.asc()) if kwargs['sort']['ac_tm'] == 'asc' else sub_query.order_by(TranslateTemplate.ac_tm.desc())

        return sub_query

    def get_client_side_dict(self, fields='id, value, type, comment, client_side, server_side', more_fields=None):
        return self.to_dict(fields, more_fields)



    @staticmethod
    def list_for_grid_tables(list, add_param, is_dict):
        new_list = []
        n = 1
        if add_param:
            new_list.append(add_param)
            n = 2
        if is_dict == False:
            list.sort()
        for s in list:
            label = list[s] if is_dict else s
            id = s if is_dict else ''
            new_list.append({
                'value': str(n),
                'label': label[0],
                'id': id
            })
            n += 1
        return new_list