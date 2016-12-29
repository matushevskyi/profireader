import time
from functools import reduce
from functools import wraps

from flask import jsonify, request, g, abort, redirect

from profapp import utils
from ..controllers import errors


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
                # return redirect(url_for('index.index'))
            end = time.clock()
            profiler = utils.db.query_filter(Profiler, name=func.__name__, blueprint_name=func.__dict__['__endpoint__']).first()
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

def get_portal(func):
    @wraps(func)
    def function_portal(*args, **kwargs):
        from ..models.portal import Portal
        return func(g.db().query(Portal).filter_by(host=request.host).first(), *args, **kwargs)

    return function_portal

def check_right(classCheck, params=None, action=None):
    def wrapped(func):
        @wraps(func)
        def decorated_view(*args, **kwargs):
            allow = True
            try:
                if not params:
                    allow = classCheck().is_allowed(raise_exception_redirect_if_not = True)
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
                            allow = instance.is_allowed(raise_exception_redirect_if_not = True)
                if allow != True:
                    abort(403)
            except errors.NoRights as e:
                return redirect(e.url)
            return func(*args, **kwargs)
        decorated_view.__check_rights__ = True
        return decorated_view
    return wrapped

