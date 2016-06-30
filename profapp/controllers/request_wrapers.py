from functools import wraps
from flask import jsonify, request, g, abort, redirect, url_for, flash
from functools import reduce
from ..controllers import errors
import time
from utils.db_utils import db

def ok(func):
    @wraps(func)
    def function_json(*args, **kwargs):
        try:
            if 'json' in kwargs:
                del kwargs['json']
            a = request.json
            ret = func(a, *args, **kwargs)
            ret = {'data': ret, 'ok': True, 'error_code': 'ERROR_NO_ERROR'}
            # template = g.req('__translate', default='')
            # if template != '':
            #     ret['__translate'] = db(TranslateTemplate, template=template)
            return jsonify(ret)
        # except Exception as e:
        except errors.ValidationException as e:
            db = getattr(g, 'db', None)
            db.rollback()
            return jsonify({'ok': False, 'error_code': -1, 'result': e.result})
    return function_json


def function_profiler(func):
    from ..models.profiler import Profiler
    @wraps(func)
    def wrapper(*args, **kwargs):

        if g.debug or g.testing:
            if not func.__dict__.get('__check_rights__'):
                print('Please add "check_right" decorator for your func!')
            start = time.clock()
            try:
                ret = func(*args, **kwargs)
            except:
                import sys
                print("Unexpected error:", sys.exc_info()[0])
                return "Unexpected error:", sys.exc_info()[0]
                # return redirect(url_for('general.index'))
            end = time.clock()
            profiler = db(Profiler, name=func.__name__, blueprint_name=func.__dict__['__endpoint__']).first()
            method = ','.join([method for method in func.__dict__['__method__']]) if func.__dict__['__method__'] else None
            if profiler:
                profiler.update_profile(end-start, method)
            else:
                Profiler().create_profile(func.__name__, func.__dict__['__endpoint__'], end-start, method)
            return ret
        else:
            if not func.__dict__['__check_rights__']:
                raise Exception('method not allowed! Please add "check_right" decorator for your func!')
            try:
                ret = func(*args, **kwargs)
            except:
                import sys
                print("Unexpected error:", sys.exc_info()[0])
                return "Unexpected error:", sys.exc_info()[0]
        return ret
    return wrapper


def replace_brackets(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs:
            for ch in ['{', '}', ' ']:
                for key in kwargs:
                    if ch in kwargs[key]:
                        kwargs[key] = kwargs[key].replace(ch, "")
        return func(*args, **kwargs)

    return wrapper


# TODO (AA to AA): may be change it to check_user_company_rights(*rights_business_rule):
def check_rights(*rights_business_rule):
    # (rights, lambda_func) = rights_lambda_rule.items()[0]
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not rights_business_rule:
                return True
            rez = reduce(lambda x, y: x or y(**kwargs), rights_business_rule, False)
            if not rez:
                abort(403)
            return func(*args, **kwargs)

        return wrapper

    return decorator

def convert_col_to_arrays(*args):
    pass


def need_we_column(name, arr, is_relationship=False):
    realname = name if name in arr else '*'
    if not is_relationship:
        if realname in arr:
            if len(arr[realname]) > 0:
                raise ValueError("you ask for sub-attribute of Column instance `%s` (not Relationship)" % (realname,))
            return True
        else:
            return False
    else:
        if realname in arr:
            if len(arr[name]) == 0:
                raise ValueError(
                    "You ask for Relationship `%s` instance, but don't ask for any sun-attribute in it" % (realname,))
            return arr[name]
        else:
            return False


def tos_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not g.user or not g.user.tos:
            # flash('You have not accept licence and terms')
            return redirect(url_for('general.index'))
        return func(*args, **kwargs)
    return decorated_view

def check_right(classCheck, params=None, action=None):
    def wrapped(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            allow = True
            if not params:
                allow = classCheck().is_allowed()
            else:
                set_attrs = [params] if isinstance(params, str) else params
                instance = classCheck()
                check = True
                for param in set_attrs:
                    if param in kwargs and kwargs[param]:
                        setattr(instance, param, kwargs[param])
                    else:
                        check = False
                if check:
                    if action:
                        if action in kwargs:
                            allow = instance.action_is_allowed(kwargs[action])
                        else:
                            allow = instance.action_is_allowed(action)
                    else:
                        allow = instance.is_allowed()
            if allow != True:
                abort(403)
            return func(*args, **kwargs)
        decorated_view.__check_rights__ = True
        return decorated_view
    return wrapped

# def object_to_dict(obj, *args, prefix=''):
#     ret = {}
#
#     req_columns = {}
#     req_relationships = {}
#     for argument in args:
#         columnsdevided = argument.split('.')
#         if len(columnsdevided) == 1:
#             req_columns[argument] = True
#         else:
#             req_relationname = columnsdevided.pop(0)
#             if req_relationname not in req_relationships:
#                 req_relationships[req_relationname] = []
#             req_relationships[req_relationname].append('.'.join(columnsdevided))
#
#     # req_columns = list(set(req_columns))
#     # req_relationships = {relationname:convert_col_to_arrays(*nextlevelcols) for relationname,nextlevelcols in relationships}
#
#     columns = class_mapper(obj.__class__).columns
#     realations = {a:b for (a,b) in  class_mapper(obj.__class__).relationships.items()}
#
#     get_key_value = lambda o: o.isoformat() if isinstance(o, datetime.datetime) else o
#     for col in columns:
#         if col.key in req_columns or '*' in req_columns:
#             ret[col.key] = get_key_value(getattr(obj, col.key))
#             if col.key in req_columns:
#                 del req_columns[col.key]
#     if '*' in req_columns:
#         del req_columns['*']
#
#     if len(req_columns) > 0:
#         columns_not_in_relations = list(set(req_columns.keys()) - set(realations.keys()))
#         if len(columns_not_in_relations) > 0:
#             raise ValueError(
#                 "you requested not existing attribute(s) `%s%s`" % (prefix, '`, `'.join(columns_not_in_relations),))
#         else:
#             raise ValueError("you requested for attribute(s) but relationships found `%s%s`" % (
#             prefix, '`, `'.join(set(realations.keys()).intersection(req_columns.keys())),))
#
#     for relationname, relation in realations.items():
#         if relationname in req_relationships or '*' in req_relationships:
#             if relationname in req_relationships:
#                 nextlevelargs = req_relationships[relationname]
#                 del req_relationships[relationname]
#             else:
#                 nextlevelargs = req_relationships['*']
#             related_obj = getattr(obj, relationname)
#             if relation.uselist:
#                 ret[relationname] = [object_to_dict(child, *nextlevelargs, prefix = prefix + relationname + '.') for child in
#                                      related_obj]
#             else:
#                 ret[relationname] = object_to_dict(related_obj, *nextlevelargs, prefix = prefix + relationname + '.')
#
#     if '*' in req_relationships:
#         del req_relationships['*']
#
#     if len(req_relationships) > 0:
#         relations_not_in_columns = list(set(req_relationships.keys()) - set(columns))
#         if len(relations_not_in_columns) > 0:
#             raise ValueError(
#                 "you requested not existing relation(s) `%s%s`" % (prefix, '`, `'.join(relations_not_in_columns),))
#         else:
#             raise ValueError("you requested for relation(s) but column(s) found `%s%s`" % (
#             prefix, '`, `'.join(set(columns).intersection(req_relationships)),))
#
#     return ret



    # for column in
    # for name, relation in class_mapper(obj.__class__).relationships.items():
    #     if name in show or show == '*':
    #         related_obj = getattr(obj, name)
    #         if show == '*':
    #             innextlevel = ['id']
    #         else:
    #             innextlevel = ['id'] if show[name] == True else show[name]
    #         if relation.uselist:
    #             ret[name] = [object_to_dict(child, innextlevel) for child in related_obj]
    #         else:
    #             ret[name] = object_to_dict(related_obj, innextlevel)
    #
    #
    # columns = class_mapper(obj.__class__).columns
    # get_key_value = lambda c: (c, getattr(obj, c).isoformat()) if isinstance(getattr(obj, c), datetime.datetime) else (c, getattr(obj, c))
    # ret = dict([get_key_value(col.key) for col in columns if col.key in show or show == '*'])
    #
    # for name, relation in class_mapper(obj.__class__).relationships.items():
    #     if name in show or show == '*':
    #         related_obj = getattr(obj, name)
    #         if show == '*':
    #             innextlevel = ['id']
    #         else:
    #             innextlevel = ['id'] if show[name] == True else show[name]
    #         if relation.uselist:
    #             ret[name] = [object_to_dict(child, innextlevel) for child in related_obj]
    #         else:
    #             ret[name] = object_to_dict(related_obj, innextlevel)




    #
    #
    # ret = {}
    # if isinstance(fields, dict):
    #     for fieldname in fields:
    #         atr = getattr(obj, fieldname)
    #         if isinstance(atr, list):
    #             ret[fieldname] = [object_to_dict(i, fields[fieldname]) for i in atr]
    #         elif isinstance(atr, Base):
    #             ret[fieldname] = object_to_dict(atr, fields[fieldname])
    #         else:
    #             ret[fieldname] = atr
    #

# mapper = class_mapper(obj.__class__)
# columns = [column.key for column in mapper.columns]
# get_key_value = lambda c: (c, getattr(obj, c).isoformat()) if isinstance(getattr(obj, c), datetime.datetime) else (c, getattr(obj, c))
# out = dict(map(get_key_value, columns))
# for name, relation in mapper.relationships.items():
#     related_obj = getattr(obj, name)
#     if relation not in found or relation.uselist:
#         found.add(relation)
#         print((obj, name, relation, relation.uselist))
#         if related_obj is not None:
#             if relation.uselist:
#                 out[name] = [object_to_dict(child, found) for child in related_obj]
#             else:
#                 out[name] = object_to_dict(related_obj, found)
#     # else:
#     #     if relation.uselist:
#     #         out[name] = [object_to_dict(child, found) for child in related_obj]
#     #     else:
#     #         out[name] = object_to_dict(related_obj, found)
#
# return out
