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


def dict_merge(*args, remove={}):
    ret = {}
    for d in args:
        ret.update(d)
    return {k: v for k, v in ret.items() if not k in remove}

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
