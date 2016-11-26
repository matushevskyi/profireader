import re


def fileUrl(id, down=False, if_no_file=None):
    from config import Config
    if not id:
        return if_no_file if if_no_file else ''

    server = re.sub(r'^[^-]*-[^-]*-4([^-]*)-.*$', r'\1', id)
    return '//file' + server + '.' + Config.MAIN_DOMAIN + '/' + id + '/' + ('?d' if down else '')


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


def static_address(relative_file_name):
    from config import Config
    return '//static.' + Config.MAIN_DOMAIN + '/static/' + relative_file_name


def find_by_id(list, id):
    return next((d for d in list if (d['id'] if isinstance(d, dict) else d.id) == id), None)


def dict_deep_replace(what_to_append, dictionary, *args, if_not_exists = False):
    indexes = list(args)
    lastindex = indexes.pop()
    for a in indexes:
        if not a in dictionary:
            dictionary[a] = {}
        dictionary = dictionary[a]
    if not if_not_exists or lastindex not in dictionary:
        dictionary[lastindex] = what_to_append


def dict_deep_inc(dictionary, *args, inc_by=1):
    indexes = list(args)
    lastindex = indexes.pop()
    for a in indexes:
        if not a in dictionary:
            dictionary[a] = {}
        dictionary = dictionary[a]
    if lastindex in dictionary:
        dictionary[lastindex] += inc_by
    else:
        dictionary[lastindex] = inc_by

def get_client_side_list(list, **kwargs):
    return [x.get_client_side_dict(**kwargs) for x in list]


def get_client_side_dict(list, **kwargs):
    return {x.id: x.get_client_side_dict(**kwargs) for x in list}


def get_from_list_by_key(list, key):
    return [x.get(key, '') for x in list]
