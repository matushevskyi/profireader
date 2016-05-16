from .pr_base import PRBase, Base
from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column
from utils.db_utils import db


class Ips(Base, PRBase):
    __tablename__ = 'ip'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    ip = Column(TABLE_TYPES['name'], default='')

    def __init__(self, id=None,  ip=None ):
        self.id = id
        self.ip = ip

    @staticmethod
    def delete(objects):
        for obj in objects:
            f = db(Ips, id=obj['id']).first()
            f.delete()
        return 'True'

    @staticmethod
    def subquery_search(template=None, url=None, **kwargs):
        sub_query = db(Ips)
        if 'filter' in kwargs:
            if 'url' in kwargs['filter']:
                sub_query = sub_query.filter_by(url=kwargs['filter']['url'])
            if 'template' in kwargs['filter']:
                sub_query = sub_query.filter_by(template=kwargs['filter']['template'])
        if 'search_text' in kwargs:
            if 'name' in kwargs['search_text']:
                sub_query = sub_query.filter(Ips.name.ilike("%" + kwargs['search_text']['name'] + "%"))
            if 'uk' in kwargs['search_text']:
                sub_query = sub_query.filter(Ips.uk.ilike("%" + kwargs['search_text']['uk'] + "%"))
            if 'en' in kwargs['search_text']:
                sub_query = sub_query.filter(Ips.en.ilike("%" + kwargs['search_text']['en'] + "%"))
        if 'cr_tm' in kwargs['sort']:
            sub_query = sub_query.order_by(Ips.cr_tm.asc()) if kwargs['sort']['cr_tm'] == 'asc' else sub_query.order_by(TranslateTemplate.cr_tm.desc())
        elif 'ac_tm' in kwargs['sort']:
            sub_query = sub_query.order_by(Ips.ac_tm.asc()) if kwargs['sort']['ac_tm'] == 'asc' else sub_query.order_by(TranslateTemplate.ac_tm.desc())


        return sub_query


    def get_client_side_dict(self, fields='id,ip', more_fields=None):
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
