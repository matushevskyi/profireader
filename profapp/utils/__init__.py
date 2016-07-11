from flask import g, request, url_for, redirect, flash
from werkzeug.exceptions import Unauthorized
from functools import wraps
import re


# we don't need it still
#
# def admin_required(fn):
#     # @wraps(fn)  # do we need it???
#     def decorated(*args, **kw):
#         if not g.user or not g.user.is_superuser:
#             raise Unauthorized('Admin permissions required')
#         return fn(*args, **kw)
#
#     return decorated

# flask.ext.login.login_required function is used instead
#
# def login_required(fn):
#     @wraps(fn)
#     def decorated(*args, **kw):
#         if g.user:
#             return fn(*args, **kw)
#         else:
#             flash('Please log in first...', 'error')
#             #  read this: http://flask.pocoo.org/snippets/62/
#             return redirect(url_for('user.login', next=request.url))
#             #next_url = request.url
#             #login_url = '%s?next=%s' % (url_for('user.login'), next_url)
#             #return redirect(login_url)
#             #raise Unauthorized('You must be logged in first')
#     return decorated

def fileUrl(id, down=False, if_no_file=None):
    if not id:
        return if_no_file if if_no_file else ''

    server = re.sub(r'^[^-]*-[^-]*-4([^-]*)-.*$', r'\1', id)
    return '//file' + server + '.profireader.com/' + id + '/' + ('?d' if down else '')


def fileID(url):
    reg = r'^(https?:)?//file(?P<server>%s{3})\.profireader\.com/(?P<id>%s{8}-%s{4}-4(%s{3})-%s{4}-%s{12})/.*$' % \
          ('[0-9a-f]', '[0-9a-f]', '[0-9a-f]', '[0-9a-f]', '[0-9a-f]', '[0-9a-f]')

    match = re.match(reg, url)
    return match.group('id') if match else None


def dict_merge(*args, remove={}, **kwargs):
    ret = {}
    for d in args:
        ret.update(d)
    ret.update(kwargs)
    return {k: v for k, v in ret.items() if not k in remove}


def dict_merge_recursive(*args):
    import collections

    def upd_rec(d, u):
        for k, v in u.items():
            if isinstance(v, collections.Mapping):
                r = upd_rec(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
        return d

    ret = {}
    for a in args:
        ret = upd_rec(ret, a)

    return ret


def list_merge(*args, remove=[]):
    ret = []
    for l in args:
        for el in l:
            if el not in ret:
                ret.append(el)
    return [el for el in ret if el not in remove]


def putInRange(what, fromr, tor, check_only=False):
    if check_only:
        return True if (what >= fromr) and (what <= tor) else False
    else:
        return fromr if (what <= fromr) else (tor if what >= tor else what)


def filter_json(json, *args, NoneTo='', ExceptionOnNotPresent=False, prefix=''):
    ret = {}
    req_columns = {}
    req_relationships = {}

    for arguments in args:
        for argument in re.compile('\s*,\s*').split(arguments):
            columnsdevided = argument.split('.')
            column_names = columnsdevided.pop(0)
            for column_name in column_names.split('|'):
                if len(columnsdevided) == 0:
                    req_columns[column_name] = NoneTo if (column_name not in json or json[column_name] is None) else \
                        json[column_name]
                else:
                    if column_name not in req_relationships:
                        req_relationships[column_name] = []
                    req_relationships[column_name].append(
                        '.'.join(columnsdevided))

    for col in json:
        if col in req_columns or '*' in req_columns:
            ret[col] = NoneTo if (col not in json or json[col] is None) else json[col]
            if col in req_columns:
                del req_columns[col]
    if '*' in req_columns:
        del req_columns['*']

    if len(req_columns) > 0:
        columns_not_in_relations = list(set(req_columns.keys()) - set(json.keys()))
        if len(columns_not_in_relations) > 0:
            if ExceptionOnNotPresent:
                raise ValueError(
                    "you requested not existing json value(s) `%s%s`" % (
                        prefix, '`, `'.join(columns_not_in_relations),))
            else:
                for notpresent in columns_not_in_relations:
                    ret[notpresent] = NoneTo

        else:
            raise ValueError("you requested for attribute(s) but "
                             "relationships found `%s%s`" % (
                                 prefix, '`, `'.join(set(json.keys()).
                                     intersection(
                                     req_columns.keys())),))

    for relationname, relation in json.items():
        if relationname in req_relationships or '*' in req_relationships:
            if relationname in req_relationships:
                nextlevelargs = req_relationships[relationname]
                del req_relationships[relationname]
            else:
                nextlevelargs = req_relationships['*']
            if type(relation) is list:
                ret[relationname] = [
                    filter_json(child, *nextlevelargs,
                                prefix=prefix + relationname + '.'
                                ) for child in
                    relation]
            else:
                ret[relationname] = None if relation is None else filter_json(relation, *nextlevelargs,
                                                                              prefix=prefix + relationname + '.')

    if '*' in req_relationships:
        del req_relationships['*']

    if len(req_relationships) > 0:
        relations_not_in_columns = list(set(
            req_relationships.keys()) - set(json))
        if len(relations_not_in_columns) > 0:
            raise ValueError(
                "you requested not existing json(s) `%s%s`" % (
                    prefix, '`, `'.join(relations_not_in_columns),))
        else:
            raise ValueError("you requested for json deeper than json is(s) but "
                             "column(s) found `%s%s`" % (
                                 prefix, '`, `'.join(set(json).intersection(
                                     req_relationships)),))

    return ret