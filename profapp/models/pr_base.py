import collections
import datetime
import operator
import re
import sys
import time
import traceback
from collections import OrderedDict

from flask import g
from sqlalchemy import Column, or_, desc, asc
from sqlalchemy import and_
from sqlalchemy.ext.associationproxy import AssociationProxy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import make_transient, class_mapper
from sqlalchemy.sql import expression
from sqlalchemy.sql import func

from config import Config
from .. import utils
from ..constants.SEARCH import RELEVANCE
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..controllers import errors

Base = declarative_base()


class DateIntervalDescriptor(object):
    def __init__(self):
        pass

    def __get__(self, instance, owner):
        res, am = instance.split(' ')
        return {'resolution': res, 'amount': am}

    # def proxy_setter(self, file_img: FileImg, client_data):
    def __set__(self, instance, data):
        if data['amount'] < 0:
            raise errors.BadDataProvided({'message': 'amount < 0'})
        if data['resolution'] not in ['days', 'years', 'weeks', 'months']:
            raise errors.BadDataProvided(
                {'message': "resolution should have following values: 'days', 'years', 'weeks', 'months'"})

        instance = "%s %s" % (int(data['amount']), data['resolution'])

        # self.id = client_data.get('id', None)
        # self.company_id = client_data.get('company_id', None)
        # self.member_company_portal_id = client_data.get('member_company_portal_id', None)
        return True


# this event is called whenever an attribute
# on a class is instrumented
# @event.listens_for(Base, 'attribute_instrument')
# def configure_listener(class_, key, inst):
#     if not hasattr(inst.property, 'columns'):
#         return
#     # this event is called whenever a "set"
#     # occurs on that instrumented attribute
#
#     @event.listens_for(inst, "set", retval=True)
#     def set_(instance, value, oldvalue, initiator):
#         validator = validators.get(inst.property.columns[0].type.__class__)
#         if validator:
#             return validator(value)
#         else:
#             return value
class Search(Base):
    __tablename__ = 'search'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True, unique=True)
    index = Column(TABLE_TYPES['id_profireader'], nullable=False)
    table_name = Column(TABLE_TYPES['short_text'], nullable=False)
    text = Column(TABLE_TYPES['text'], nullable=False)
    relevance = Column(TABLE_TYPES['int'], nullable=False)
    kind = Column(TABLE_TYPES['short_text'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    position = Column(TABLE_TYPES['position'])

    def __init__(self, index=None, table_name=None, text=None, relevance=None, kind=None,
                 position=None, md_tm=datetime.datetime.now(), **kwargs):
        """ **kwargs: This parameters optionally, and useful when you will use search function.
                      You can pass kwargs arguments in class constructor or when call function.
                      search_text = string text for search,
                      pagination = boolean, default True
                      , if True this func return n numbers elements which produce in pagination
                      page = integer current page for pagination,
                      items_per_page = integer items per page for pagination
                      , default Config.ITEMS_PER_PAGE,
                      order_by = (string, integer, tuple or list)
                      ,string :(with field for which you want sort)
                      ,integer: (position, relevance, md_tm default=relevance)
                      (USE CONSTANTS IN SEARCH CLASS)
                      ,tuple or list: multiple fields which you want to use.
                      desc_asc = sort by desc or asc default = desc """
        self.index = index
        self.table_name = table_name
        self.text = text
        self.relevance = relevance
        self.kind = kind
        self.position = position
        self.md_tm = md_tm
        self.__order_by_to_str = {1: 'relevance', 2: 'position', 3: 'md_tm'}
        self.__page = None
        self.__items_per_page = None
        self.__pagination = None
        self.__desc_asc = None
        self.__pages = None
        self.__search_text = None
        self.__return_objects = None
        self.__start_reloading = lambda *args: self.__search_start(*args, **self.__dict__)

    ORDER_RELEVANCE = 1
    ORDER_POSITION = 2
    ORDER_MD_TM = 3

    # TODO: OZ by OZ: remove this function after replacement
    def search(self, *args: dict, **kwargs):
        """ *args: dictionary with following values -
                             -class = sqlalchemy table class object,
                optional:    -filter: sqlalchemy filter with your own parameters,
                optional:    -fields: (tuple ot list) with fields name from table Search.kind
                             , if provided and search_text is not None, this function will look
                             for search text only in this fields.
                             -tags: boolean. If True, function will return dict with fields
                             updated with tags
                optional:    -return_fields: String. If return_fields provided,
                             this function return dictionary with fields you want, else return id's.
                             example: "name,country,region". Also you can pass to this argument
                             string 'default_dict' which also return sorted dictionaries with
                             default fields provided in 'get_client_side_to_dict' func
                             for this class.
                if you want to pass one fieldname you almost should make tuple
                or list. example: ('title', ):
                optional:    -join: subquery wich you want to join without filters.
            For example: {'class': Company,
                          'filter': ~db(User, company_id=1).exists(),
                          'join': Article,
                          'fields': (tuple) with fields name in table Search.kind}
            default: {'class': class,
                      'filter': class.id == Search.index,
                      'join': class,
                      'fields': all_fields}
            ** kwargs optional
            **kwargs: -search_text = string text for search,
                      -pagination = boolean, default True
                      , if True this func return n numbers elements which produce in pagination
                      -page = integer current page for pagination,
                      -items_per_page = integer items per page for pagination
                      , default Config.ITEMS_PER_PAGE,
                      -order_by = (string, integer, tuple or list)
                      ,string :(with field for which you want sort)
                      ,integer: (position, relevance, md_tm default=relevance)
                      (USE CONSTANTS IN SEARCH CLASS)
                      ,tuple or list: multiple fields which you want to use. For example:
                      if you have multiple args and different fields you want to sort in
                      , you can use list:
                      example:
                      {'class': Company,
                       'filter': ~db(User, company_id=1).exists(),
                       'join': Article,
                       'fields': (tuple) with fields name in table Search.kind},
                       {'class': ArticlePortalDivision,
                        'filter' and_(ArticlePortalDivision.portal_division_id == division.id,
                                      ArticlePortalDivision.status ==
                                      ArticlePortalDivision.STATUSES['PUBLISHED'])},
                        order_by = ('name', 'title', ). Because class Company does not have 'title'
                        field, and class ArticlePortalDivision does not have 'name' field.
                      -desc_asc = sort by desc or asc default = desc,
                      :return id's objects or objects which you want, all pages for pagination
                       and current page """
        self.__dict__.update(**kwargs)
        assert all(filter(lambda arg: type(arg) is dict, args)), '*args should be a dictionary'
        self.__init_arguments(*args, **self.__dict__)
        self.__catch_errors(*args, ord_by=kwargs.get('order_by'))
        return self.__search_start(*args, **self.__dict__)

    def __init_arguments(self, *args, **kwargs):
        self.__page = kwargs.get('page') or 1
        self.__items_per_page = kwargs.get('items_per_page') or getattr(Config, 'ITEMS_PER_PAGE')
        self.__pagination = kwargs.get('pagination') or True
        self.__desc_asc = kwargs.get('desc_asc') or 'desc'
        self.__pages = None
        self.__search_text = kwargs.get('search_text') or ''
        self.__return_objects = any(list(map(lambda arg: bool(arg.get('return_fields')), args)))

    def __search_start(self, *args: dict, **kwargs):
        """ Don't use this method, use Search().search() method """
        subquery_search = self.__get_subquery(*args, ord_by=kwargs.get('order_by'))
        if self.__pagination:
            from ..controllers.pagination import pagination as pagination_func
            subquery_search, self.__pages, page, _ = pagination_func(subquery_search, page=self.__page,
                                                                     items_per_page=self.__items_per_page)
        subquery_search = subquery_search.subquery()
        join_search = []
        for arg in args:
            join_params = arg.get('join') or arg['class']
            join_search.append(utils.db.query_filter(subquery_search).join(join_params,
                                                                  arg['class'].id == subquery_search.c.index).subquery())
        objects = collections.OrderedDict()
        to_order = {}
        _order_by = kwargs.get('order_by') or Search.ORDER_MD_TM
        ord_by = 'text' if type(_order_by) in (str, list, tuple) \
            else self.__order_by_to_str[_order_by]
        for search in join_search:
            for cls in utils.db.query_filter(search).all():
                objects[cls.index] = {'id': cls.index, 'table_name': cls.table_name,
                                      'order': getattr(cls, ord_by), 'md_tm': cls.md_tm}
                to_order[cls.index] = (getattr(cls, ord_by), getattr(cls, 'md_tm'))
        objects = {obj['id']: obj for obj in
                   collections.OrderedDict(sorted(objects.items())).values()}
        ordered = sorted(tuple(to_order.items()), reverse=False if self.__desc_asc == 'asc' else True,
                         key=operator.itemgetter(1))
        self.__reload_func(len(ordered), *args)
        if self.__return_objects:
            objects = self.__get_objects_from_db(*args, ordered_objects_list=ordered)
        else:
            objects = collections.OrderedDict((id, objects[id]) for id, ord in ordered)
        return objects, self.__pages, self.__page

    def __reload_func(self, elements_length, *args):
        if elements_length or (len(args) == 1):
            return
        else:
            args = list(args)
            for arg in args:
                if not self.__get_subquery(arg, ord_by=Search.ORDER_MD_TM).limit(1).count():
                    args.remove(arg)
            self.__start_reloading(*args)

    def __get_subquery(self, *args, ord_by=None):
        def add_joined_search(field_name):
            joined = utils.db.query_filter(Search.index, func.min(Search.text).label('text'),
                                  func.min(Search.table_name).label('table_name'),
                                  index=subquery_search.subquery().c.index).filter(
                Search.kind.in_(tuple(field_name))).group_by(Search.index)
            return joined

        subquery_search = utils.db.query_filter(Search.index.label('index'),
                                       func.sum(Search.relevance).label('relevance'),
                                       func.min(Search.table_name).label('table_name'),
                                       func.min(Search.md_tm).label('md_tm'),
                                       func.max(Search.position).label('position'),
                                       func.max(Search.text).label('text')).filter(
            or_(*self.__get_search_params(*args))).group_by('index')
        if type(ord_by) in (str, list, tuple):
            order = self.__get_order('text', 'text')
            subquery_search = add_joined_search(ord_by)
        elif type(ord_by) == int:
            ord_to_str = self.__order_by_to_str[ord_by]
            order = self.__get_order(ord_to_str, ord_to_str)
        else:
            order = self.__get_order('relevance', 'relevance')
        if 'md_tm' in str(order):
            subquery_search = subquery_search.order_by(order)
        else:
            subquery_search = subquery_search.order_by(order).order_by(
                self.__get_order('md_tm', 'md_tm'))
        return subquery_search

    def __get_order(self, order_name, field):
        order_name += '+' if self.__desc_asc == 'desc' else '-'
        result = {'text+': lambda field_name: desc(func.max(getattr(Search, field_name, Search.text))),
                  'text-': lambda field_name: asc(func.max(
                      getattr(Search, field_name, Search.text))),
                  'md_tm+': lambda field_name: desc(func.min(
                      getattr(Search, field_name, Search.md_tm))),
                  'md_tm-': lambda field_name: asc(func.min(
                      getattr(Search, field_name, Search.md_tm))),
                  'relevance+': lambda field_name: desc(func.sum(
                      getattr(Search, field_name, Search.relevance))),
                  'relevance-': lambda field_name: asc(func.sum(
                      getattr(Search, field_name, Search.relevance))),
                  'position+': lambda field_name: desc(func.max(
                      getattr(Search, field_name, Search.position))),
                  'position-': lambda field_name: asc(func.max(
                      getattr(Search, field_name, Search.position)))
                  }[order_name](field)
        return result

    def __get_objects_from_db(self, *args, ordered_objects_list=None):
        items = dict()
        for cls in args:
            fields = cls.get('return_fields') or 'id'
            tags = cls.get('tags')
            assert type(fields) is str, \
                'Arg parameter return_fields must be string but %s given' % fields
            for a in utils.db.query_filter(cls['class']).filter(cls['class'].id.in_(
                    list(map(lambda x: x[0], ordered_objects_list)))).all():
                if fields != 'default_dict' and not tags:
                    items[a.id] = a.get_client_side_dict(fields=fields)
                elif fields != 'default_dict' and tags:
                    items[a.id] = a.get_client_side_dict(fields=fields)
                    items[a.id].update(dict(tags=a.tags))
                elif fields == 'default_dict' and not tags:
                    items[a.id] = a.get_client_side_dict()
                else:
                    items[a.id] = a.get_client_side_dict()
                    items[a.id].update(dict(tags=a.tags))
        return collections.OrderedDict((id, items[id]) for id, val in ordered_objects_list)

    def __get_search_params(self, *args: dict):
        search_params = []
        for arg in args:
            filter_params = arg.get('filter')
            fields = arg.get('fields') or [key for key in vars(arg['class']).keys() if not key.startswith('_')]
            assert type(fields) is list or tuple, \
                'Arg parameter fields should be list or tuple but %s given' % type(fields)
            if filter_params is None:
                filter_array = [Search.index == utils.db.query_filter(arg['class'].id).subquery().c.id]
            else:
                filter_array = [Search.index == utils.db.query_filter(arg['class'].id).filter(filter_params).subquery().c.id]
            filter_array.append(Search.table_name == arg['class'].__tablename__)
            filter_array.append(Search.kind.in_(fields))
            search_text = self.__search_text
            if search_text:
                filter_array.append(Search.text.ilike("%" + search_text + "%"))
            search_params.append(and_(*filter_array))
        return search_params

    def __catch_errors(self, *args, ord_by=None):
        try:
            assert (self.__desc_asc == 'desc' or self.__desc_asc == 'asc'), \
                'Parameter desc_asc should be desc or asc but %s given' % self.__desc_asc
            assert type(self.__search_text) is str, \
                'Parameter search_text should be string but %s given' % type(self.__search_text)
            assert type(args[0]) is dict, \
                'Args should be dictionaries with class of model but %s inspected' % type(args[0])
            assert type(self.__pagination) is bool, \
                'Parameter pagination should be boolean but %s given' % type(self.__pagination)
            assert (type(self.__page), type(self.__items_per_page) is int) and self.__page >= 0, \
                'Parameter page is not integer, or page < 1 .'
            assert (getattr(args[0]['class'], str(ord_by), False) is not False) or \
                   (type(ord_by) is int) or type(
                ord_by is (list or tuple)), \
                'Bad value for parameter "order_by".' \
                'You requested attribute which is not in class %s or give bad kwarg type.' \
                'Can be string, list or tuple %s given' % \
                (args[0]['class'], type(ord_by))
            assert type(self.__return_objects) is bool, \
                'Parameter "return_objects" must be boolean but %s given' % type(self.__return_objects)
        except AssertionError as e:
            _, _, tb = sys.exc_info()
            traceback.print_tb(tb)
            tb_info = traceback.extract_tb(tb)
            filename_, line_, func_, text_ = tb_info[-1]
            message = 'An error occurred on File "{file}" line {line}\n {assert_message}'.format(
                line=line_, assert_message=e.args, file=filename_)
            raise errors.BadDataProvided({'message': message})


class Grid:
    @staticmethod
    def filter_for_status(statuses):
        return [{'value': status, 'label': status} for status in statuses.keys()]

    @staticmethod
    def page_options(client_json):
        return {'page': client_json['pageNumber'], 'getPageOfId': client_json.get('pageNumber'),
                'items_per_page': client_json['pageSize']} if client_json else {}

    @staticmethod
    def subquery_grid(query, filters=None, sorts=None):
        if filters:
            for filter in filters:
                if filter['type'] == 'text':
                    query = query.filter(filter['field'].ilike("%" + filter['value'] + "%"))
                elif filter['type'] == 'text_multi':
                    query = query.filter(or_(v.ilike("%" + filter['value'] + "%") for v in filter['field']))
                elif filter['type'] == 'select':
                    query = query.filter(filter['field'] == filter['value'])
                elif filter['type'] == 'date_range':
                    fromm = datetime.datetime.utcfromtimestamp((filter['value']['from']) / 1000)
                    to = datetime.datetime.utcfromtimestamp((filter['value']['to'] + 86399999) / 1000)
                    query = query.filter(filter['field'].between(fromm, to))
                elif filter['type'] == 'range':
                    query = query.filter(filter['field'].between(filter['value']['from'], filter['value']['to']))
                elif filter['type'] == 'multiselect':
                    query = query.filter(or_(filter['field'] == v for v in filter['value']))
        if sorts:
            for sort in sorts:
                query = query.order_by(sort['field'].asc()) if sort['value'] == 'asc' else query.order_by(
                    sort['field'].desc())
        return query

    @staticmethod
    def grid_tuple_to_dict(tuple):
        list = []
        for t in tuple:
            list.extend([t[0]] + t[1])
        return list


class PRBase:
    # TODO: OZ by OZ: for what is this property?
    omit_validation = False

    # search_fields = {}

    def __init__(self):
        self.query = g.db.query_property()

    # TODO: YG by OZ: move this (to next comment) static methods to tools (just like `putInRange` moved)

    @classmethod
    def get_page(cls, select_from=None, order_by=None, filter=None, page=1, per_page=10):
        page = 1 if page is None else page
        per_page = 10 if per_page is None else per_page
        sel_from = cls if select_from is None else select_from
        ord = desc(sel_from.id) if order_by is None else order_by
        sql = g.db.query(sel_from)
        if filter is not None:
            sql = sql.filter(filter)
        ret = sql.order_by(ord).limit(per_page + 1).offset((page - 1) * per_page).all()
        return ret[0:per_page], page + 1 if len(ret) > per_page else -1,

    @staticmethod
    def get_ordered_dict(list_of_dicts, **kwargs):
        ret = OrderedDict()
        for item in list_of_dicts:
            ret[item['id']] = item
        return ret

    @classmethod
    def get_all_active_ordered_by_position(classname, **kwargs):
        return [e.get_client_side_dict(**kwargs) for e in
                utils.db.query_filter(classname).filter_by(active=True).order_by(classname.position).all()]

    @staticmethod
    def str2float(str, onfail=None):
        try:
            return float(str)
        except Exception:
            return onfail

    @staticmethod
    def str2int(str, onfail=None):
        try:
            return int(str)
        except Exception:
            return onfail

    @staticmethod
    def parse_timestamp(str):
        try:
            return datetime.datetime.strptime(str, "%a, %d %b %Y %H:%M:%S %Z")
        except:
            return None

    @staticmethod
    def parse_date(str):
        try:
            return datetime.date.strptime(str, "%Y-%m-%d")
        except:
            return None

    @staticmethod
    def del_attr_by_keys(dict, keys):
        return {key: dict[key] for key in dict if key not in keys}

    # TODO: YG by OZ: move this static methods to tools


    def position_unique_filter(self):
        return self.__class__.position != None

    # if insert_after_id == False - insert at top
    # if insert_after_id == True - insert at bottom
    # if insert_after_id == Null - set null (element is not positioned)
    # if else - insert after given id
    def insert_after(self, insert_after_id, filter=None):

        tochange = utils.db.query_filter(self.__class__)

        if filter is not None:
            tochange = tochange.filter(filter)

        if insert_after_id == False:
            oldtop = tochange.order_by(expression.desc(self.__class__.position)).first()
            if oldtop and (oldtop.id != self.id):
                self.position = None
                self.save()
                self.position = oldtop.position + 1
            elif not oldtop:
                self.position = None
                self.save()
                self.position = 1
        elif insert_after_id == True:
            oldbottom = tochange.order_by(expression.asc(self.__class__.position)).first()
            if oldbottom and (oldbottom.id != self.id):
                self.position = None
                self.save()
                tochange.update({'position': self.__class__.position + 1})
                self.position = 1
            elif not oldbottom:
                self.position = None
                self.save()
                self.position = 1
        elif insert_after_id is None:
            self.position = None
        elif self.id != insert_after_id:
            insert_after_object = self.get(insert_after_id)
            if self.position != insert_after_object.position - 1:
                self.position = None
                self.save()
                tochange = tochange.filter(self.__class__.position >= insert_after_object.position)
                tochange.update({'position': self.__class__.position + 1})
                self.position = insert_after_object.position - 1

        return self

    @staticmethod
    def DEFAULT_VALIDATION_ANSWER():
        return {'errors': {}, 'warnings': {}, 'notices': {}}

    def validate(self, is_new=False, regexps={}):
        ret = self.DEFAULT_VALIDATION_ANSWER()

        for (atr, regexp) in regexps.items():
            if not re.match(regexp, getattr(self, atr)):
                ret['errors'][atr] = "%s should match regexp %s" % (atr, regexp)
        return ret

    @staticmethod
    def validation_append_by_ids(validation_result, collection, *dict_indicies):
        for item in collection:
            append = item.validate()
            for k in ['errors', 'warnings', 'notices']:
                if k in append and append[k]:
                    utils.dict_deep_replace(append[k], validation_result, *((k,) + dict_indicies + (item.id,)))

    def delete(self):
        g.db.delete(self)
        g.db.commit()

    def refresh(self):
        g.db.refresh(self)
        return self

    def save(self):
        g.db.add(self)
        g.db.flush()
        return self

    def attr(self, dictionary={}, **kwargs):
        for k in dictionary:
            setattr(self, k, dictionary[k])
        for k in kwargs:
            setattr(self, k, kwargs[k])
        return self

    def attr_filter(self, dictionary, *filters):
        self.attr(utils.filter_json(dictionary, *filters))

    def detach(self):
        if self in g.db:
            g.db.expunge(self)
            make_transient(self)

        self.id = None
        return self

    # def expunge(self):
    #     g.db.expunge(self)
    #     return self

    def get_client_side_dict(self, fields='id',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @classmethod
    def get(cls, id, returnNoneIfNotExists=False):
        return g.db().query(cls).filter(cls.id == id).first() if returnNoneIfNotExists else g.db().query(cls).filter(
            cls.id == id).one()

    def to_dict_object_property(self, object_name):
        object_property = getattr(self, object_name)
        if isinstance(object_property, datetime.datetime):
            return object_property.replace(object_property.year, object_property.month, object_property.day,
                                           object_property.hour, object_property.minute, object_property.second, 0)
            # return object_property.replace(object_property.year, object_property.month, object_property.day,
            #                            object_property.hour, object_property.minute, object_property.second,
            #                            0).strftime("%a, %d %b %Y %H:%M:%S")
        elif isinstance(object_property, datetime.date):
            return object_property.strftime('%Y-%m-%d')
        elif isinstance(object_property, dict):
            return object_property
        else:
            return object_property

            # TODO: OZ by OZ:**kwargs should accept lambdafunction for fields formattings

    def to_dict(self, *args, prefix=''):
        # TODO: OZ by OZ: this function is wrong. we need walk through requested fields and return appropriate attribute.
        # Now we walk through attribute (yes?)
        ret = {}
        __debug = True

        req_columns = {}
        req_relationships = {}

        def add_to_req_relationships(column_name, columns):
            if column_name not in req_relationships:
                req_relationships[column_name] = []
            req_relationships[column_name].append(columns)

        def get_next_level(child, nextlevelargs, prefix, standard_fields_required):
            in_next_level_dict = {k: v for k, v in child.items() if k in nextlevelargs} if \
                isinstance(child, dict) else child.to_dict(*nextlevelargs, prefix=prefix)
            if standard_fields_required:
                in_next_level_dict.update(child if isinstance(child, dict) else child.get_client_side_dict())
            return in_next_level_dict

        for arguments in args:
            if arguments:
                for argument in re.compile('\s*,\s*').split(arguments):
                    columnsdevided = argument.split('.')
                    column_names = columnsdevided.pop(0)
                    for column_name in column_names.split('|'):
                        if len(columnsdevided) == 0:
                            req_columns[column_name] = True
                        else:
                            add_to_req_relationships(column_name, '.'.join(columnsdevided))

        columns = class_mapper(self.__class__).columns
        relations = {a: b for (a, b) in class_mapper(self.__class__).relationships.items()}
        for a, b in class_mapper(self.__class__).all_orm_descriptors.items():
            if isinstance(b, AssociationProxy):
                relations[a] = b
        # association_proxies = {a: b for (a, b) in class_mapper(self.__class__).all_orm_descriptors.items()
        #                        if isinstance(b, AssociationProxy)}
        pass

        for col in columns:
            if col.key in req_columns or (__debug and '*' in req_columns):
                ret[col.key] = self.to_dict_object_property(col.key)
                if col.key in req_columns:
                    del req_columns[col.key]
        if '*' in req_columns and __debug:
            del req_columns['*']

        del_req_columns_in_attrs = []
        for colname in req_columns:
            if hasattr(self, colname) and colname not in relations:
                del_req_columns_in_attrs.append(colname)
                ret[colname] = getattr(self, colname)
        for colname in del_req_columns_in_attrs:
            del req_columns[colname]

        if len(req_columns) > 0:
            columns_not_in_relations = list(set(req_columns.keys()) - set(relations.keys()))
            if len(columns_not_in_relations) > 0:
                raise ValueError(
                    "you requested not existing attribute(s) `%s%s`" % (
                        prefix, '`, `'.join(columns_not_in_relations),))
            else:
                for rel_name in req_columns:
                    add_to_req_relationships(rel_name, '~')
                    # raise ValueError("you requested for attribute(s) but "
                    #                  "relationships found `%s%s`" % (
                    #                      prefix, '`, `'.join(set(relations.keys()).
                    #                          intersection(
                    #                          req_columns.keys())),))

        for relationname, relation in relations.items():
            rltn = relations[relation.target_collection] if isinstance(relation, AssociationProxy) else relation
            if relationname in req_relationships or (__debug and '*' in req_relationships):
                if relationname in req_relationships:
                    nextlevelargs = req_relationships[relationname]
                    del req_relationships[relationname]
                else:
                    nextlevelargs = req_relationships['*']
                related_obj = getattr(self, relationname)
                standard_fields_required = False
                while '~' in nextlevelargs:
                    standard_fields_required = True
                    nextlevelargs.remove('~')

                if rltn.uselist:
                    add = [get_next_level(child, nextlevelargs, prefix + relationname + '.', standard_fields_required)
                           for child in related_obj]
                else:
                    add = None if related_obj is None else \
                        get_next_level(related_obj, nextlevelargs, prefix + relationname + '.',
                                       standard_fields_required)

                ret[relationname] = add

        if '*' in req_relationships:
            del req_relationships['*']

        del_req_columns_in_attrs = []
        for relname, nextlevelargs in req_relationships.items():
            if hasattr(self, relname):
                del_req_columns_in_attrs.append(relname)
                add = utils.filter_json(getattr(self, relname), *nextlevelargs) if nextlevelargs else getattr(
                    self, relname)
                ret[relname] = utils.dict_merge_recursive(ret[relname] if relname in ret else {}, add)

        for colname in del_req_columns_in_attrs:
            del req_relationships[colname]

        if len(req_relationships) > 0:
            relations_not_in_columns = list(set(
                req_relationships.keys()) - set(columns))
            if len(relations_not_in_columns) > 0:
                raise ValueError(
                    "you requested not existing relation(s) `%s%s`" % (
                        prefix, '`, `'.join(relations_not_in_columns),))
            else:
                raise ValueError("you requested for relation(s) but "
                                 "column(s) found `%s%s`" % (
                                     prefix, '`, `'.join(set(columns).intersection(
                                         req_relationships)),))

        return ret

    def search_filter_default(self, division_id):
        """ :param division_id: 'string with id from table portal_division'
            :return: dict with prepared filter parameters for search method """
        pass

    @staticmethod
    def validate_before_update(mapper, connection, target):
        ret = target.validate(False)
        if len(ret['errors'].keys()):
            raise errors.ValidationException(ret)

    @staticmethod
    def validate_before_insert(mapper, connection, target):
        ret = target.validate(True)
        if len(ret['errors'].keys()):
            raise errors.ValidationException(ret)

    # @staticmethod
    # def validate_before_delete(mapper, connection, target):
    #     ret = target.validate('delete')
    #     if len(ret['errors'].keys()):
    #         raise errors.ValidationException(ret)

    @staticmethod
    def strip_tags(text):
        return utils.strip_tags(text)

    @staticmethod
    def add_to_search(mapper=None, connection=None, target=None):

        if hasattr(target, 'search_fields'):
            target_fields = ','.join(target.search_fields.keys())
            target_dict = target.get_client_side_dict(fields=target_fields + ',id')
            options = {'relevance': lambda field_name: getattr(RELEVANCE, field_name),
                       'processing': lambda text: utils.strip_tags(text),
                       'index': lambda target_id: target_id}
            default_time = datetime.datetime.now()
            time = default_time
            if hasattr(target, 'publishing_tm'):
                time = getattr(target, 'publishing_tm', default_time)
            elif hasattr(target, 'md_tm'):
                time = getattr(target, 'md_tm', default_time)
            elif hasattr(target, 'cr_tm'):
                time = getattr(target, 'cr_tm', default_time)
            for field in target_fields.split(','):
                field_options = target.search_fields[field]
                field_options.update({key: options[key] for key in options
                                      if key not in field_options.keys()})
                pos = getattr(target, 'position', 0)
                position = pos if pos else 0
                g.db.add(Search(index=field_options['index'](target_dict['id']),
                                table_name=target.__tablename__,
                                relevance=field_options['relevance'](field), kind=field,
                                text=field_options['processing'](str(target_dict[field])),
                                position=position, md_tm=time))

    @staticmethod
    def update_search_table(mapper=None, connection=None, target=None):

        if hasattr(target, 'search_fields'):
            if PRBase.delete_from_search(mapper, connection, target):
                PRBase.add_to_search(mapper, connection, target)
            else:
                PRBase.add_to_search(mapper, connection, target)

    @staticmethod
    def delete_from_search(mapper, connection, target):
        if hasattr(target, 'search_fields') and utils.db.query_filter(Search, index=target.id).count():
            utils.db.query_filter(Search, index=target.id).delete()
            return True
        return False

        # def elastic_insert(self):
        #     pass
        #
        # def elastic_update(self):
        #     pass
        #
        # def elastic_delete(self):
        #     pass
        #
        # @staticmethod
        # def after_insert(mapper=None, connection=None, target=None):
        #     target.elastic_insert()
        #
        # @staticmethod
        # def after_update(mapper=None, connection=None, target=None):
        #     target.elastic_update()
        #
        # @staticmethod
        # def after_delete(mapper=None, connection=None, target=None):
        #     target.elastic_delete()

        # @classmethod
        # def __declare_last__(cls):
        #     event.listen(cls, 'before_update', cls.validate_before_update)
        #     event.listen(cls, 'before_insert', cls.validate_before_insert)
        #     # event.listen(cls, 'before_delete', cls.validate_before_delete)
        # event.listen(cls, 'after_insert', cls.add_to_search)
        # event.listen(cls, 'after_update', cls.update_search_table)
        # event.listen(cls, 'after_delete', cls.delete_from_search)

        # event.listen(cls, 'after_insert', cls.after_insert)
        # event.listen(cls, 'after_update', cls.after_update)
        # event.listen(cls, 'after_delete', cls.after_delete)

    # @staticmethod
    # def datetime_from_utc_to_local(utc_datetime, format):
    #     now_timestamp = time.time()
    #     offset = datetime.datetime.fromtimestamp(now_timestamp) - datetime.datetime.utcfromtimestamp(now_timestamp)
    #     utc_datetime = utc_datetime + offset
    #     return datetime.datetime.strftime(utc_datetime, format)

#
#
#
# @event.listens_for(PRBase, 'before_insert')
# def validate_insert(mapper, connection, target):
#     ret = target.validate('insert')
#     if len(ret['errors'].keys()):
#         raise errors.ValidationException(ret)
#
# @event.listens_for(PRBase, 'before_delete')
# def validate_delete(mapper, connection, target):
#     ret = target.validate('delete')
#     if len(ret['errors'].keys()):
#         raise errors.ValidationException(ret)
#
# @event.listens_for(PRBase, 'before_update')
# def validate_update(mapper, connection, target):
#     ret = target.validate('update')
#     if len(ret['errors'].keys()):
#         raise errors.ValidationException(ret)
#
# event.listen(PRBase, 'before_update', validate_update)
# event.listen(ArticlePortal, 'before_insert', set_long_striped)
# event.listen(ArticleCompany, 'before_update', set_long_striped)
# event.listen(ArticleCompany, 'before_insert', set_long_striped)
