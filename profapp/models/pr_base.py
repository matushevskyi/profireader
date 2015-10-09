# from db_init import g.db, Base
from sqlalchemy import Table, Column, Integer, Text, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship, backref, make_transient, class_mapper
import datetime
import re
from flask import g
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import event
from utils.validators import validators

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# this event is called whenever an attribute
# on a class is instrumented
@event.listens_for(Base, 'attribute_instrument')
def configure_listener(class_, key, inst):
    if not hasattr(inst.property, 'columns'):
        return
    # this event is called whenever a "set"
    # occurs on that instrumented attribute

    @event.listens_for(inst, "set", retval=True)
    def set_(instance, value, oldvalue, initiator):
        validator = validators.get(inst.property.columns[0].type.__class__)
        if validator:
            return validator(value)
        else:
            return value


class PRBase:
    def __init__(self):
        self.query = g.db.query_property()

    def save(self):
        g.db.add(self)
        g.db.flush()
        return self

    def update(self, **kwargs):
        self.update(**kwargs)
        return self

    def attr(self, dictionary):
        for k in dictionary:
            setattr(self, k, dictionary[k])
        return self

    def detach(self):
        g.db.expunge(self)
        make_transient(self)
        self.id = None
        return self

    def expunge(self):
        g.db.expunge(self)
        return self

    def get_client_side_dict(self, fields='id'):
        return self.to_dict(fields)

    @classmethod
    def get(cls, id):
        return g.db().query(cls).get(id)

# TODO: OZ by OZ:**kwargs should accept lambdafunction for fields formattings
    def to_dict(self, *args, prefix=''):
        ret = {}

        req_columns = {}
        req_relationships = {}

        for arguments in args:

            for argument in re.compile('\s*,\s*').split(arguments):
                columnsdevided = argument.split('.')
                column_names = columnsdevided.pop(0)
                for column_name in column_names.split('|'):
                    if len(columnsdevided) == 0:
                        req_columns[column_name] = True
                    else:
                        if column_name not in req_relationships:
                            req_relationships[column_name] = []
                        req_relationships[column_name].append(
                            '.'.join(columnsdevided))

        columns = class_mapper(self.__class__).columns
        relations = {a: b for (a, b) in class_mapper(self.__class__).relationships.items()}

        get_key_value = lambda o: o.strftime('%c') if isinstance(
            o, datetime.datetime) else o
        for col in columns:
            if col.key in req_columns or '*' in req_columns:
                ret[col.key] = get_key_value(getattr(self, col.key))
                if col.key in req_columns:
                    del req_columns[col.key]
        if '*' in req_columns:
            del req_columns['*']

        if len(req_columns) > 0:
            columns_not_in_relations = list(set(req_columns.keys()) - set(relations.keys()))
            if len(columns_not_in_relations) > 0:
                raise ValueError(
                    "you requested not existing attribute(s) `%s%s`" % (
                        prefix, '`, `'.join(columns_not_in_relations),))
            else:
                raise ValueError("you requested for attribute(s) but "
                                 "relationships found `%s%s`" % (
                    prefix, '`, `'.join(set(relations.keys()).
                                        intersection(
                            req_columns.keys())),))

        for relationname, relation in relations.items():
            if relationname in req_relationships or '*' in \
                    req_relationships:
                if relationname in req_relationships:
                    nextlevelargs = req_relationships[relationname]
                    del req_relationships[relationname]
                else:
                    nextlevelargs = req_relationships['*']
                related_obj = getattr(self, relationname)
                if relation.uselist:
                    ret[relationname] = [
                        child.to_dict(*nextlevelargs,
                                      prefix=prefix + relationname + '.'
                                      ) for child in
                                         related_obj]
                else:
                    ret[relationname] = None if related_obj is None else related_obj.to_dict(*nextlevelargs, prefix=prefix + relationname + '.')

        if '*' in req_relationships:
            del req_relationships['*']

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

        # @staticmethod
        # def searchResult(collection, convert_item = lambda item: item.dict()):
        #     ret = {}
        #     for x in collection:
        #         ret[x.id] = convert_item(x)
        #
        #     return ret
