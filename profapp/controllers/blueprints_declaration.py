from flask import Blueprint
from profapp.models.permissions import Permissions
import sys
import traceback

# class PrOldBlueprint(Blueprint):
#    declared_endpoints = {}
#
#    def you_have_no_permission(self):
#        raise Exception('You have no permission')
#
#    def route(self, rule, **options):
#        from .request_wrapers import ok
#        def decorator(f):
#
#            f.__endpoint__ = self.name
#            f.__method__ = options['methods'] if 'methods' in options else ["GET"]
#            if options and 'methods' in options and 'OK' in options['methods'] and self.name in self.declared_endpoints \
#                    and f.__name__ in self.declared_endpoints[self.name]:
#                options['methods'][options['methods'].index('OK')] = 'POST'
#            if self.name in self.declared_endpoints and f.__name__ in self.declared_endpoints[self.name]:
#                ret = self.declared_endpoints[self.name][f.__name__]
#            else:
#                ret = f
#                if options and 'methods' in options and 'OK' in options['methods']:
#                    options['methods'][options['methods'].index('OK')] = 'POST'
#                    ret = ok(f)
#                    # ret = function_profiler(ret)
#                    self.declared_endpoints[self.name] = {}
#                    self.declared_endpoints[self.name][ret.__name__] = ret
#                else:
#                    # ret = function_profiler(ret)
#                    self.declared_endpoints[self.name] = {}
#                    self.declared_endpoints[self.name][ret.__name__] = ret
#            endpoint = options.pop("endpoint", ret.__name__)
#             self.add_url_rule(rule, endpoint, ret, **options)
#
#             return ret
#
#         return decorator


class PrBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        self.registered_functions = {}
        super(PrBlueprint, self).__init__(*args, **kwargs)

    def route(self, rule, **options):
        from flask import request, render_template, session, redirect, url_for, g, jsonify, current_app
        from ..models import exceptions
        from functools import wraps
        if options and 'methods' in options and 'OK' in options['methods']:
            options['methods'][options['methods'].index('OK')] = 'POST'
            ok_method = True
        else:
            ok_method = False

        if options and 'permissions' in options:
            permissions = options['permissions']
            if not isinstance(permissions, Permissions):
                raise Exception('permission have to be Permission object for blueprint={}, rule={}'.format(
                    self.name, rule))
            del options['permissions']
        else:
            raise exceptions.RouteWithoutPermissions(
                'permission have to be Permission object for blueprint={}, rule={}'.format(
                    self.name, rule))

        def decorator(f):
            @wraps(f)
            def wrapped_function(*args, **kwargs):
                print(request.base_url, request.method, f.__name__)
                method = request.method
                if method == 'POST' and ok_method:
                    method = 'OK'
                # hide_error = not (g.debug or g.testing)

                try:
                    ps = getattr(wrapped_function, '_permissions', None)
                    # print(request.url_rule.rule, wrapped_function._permissions)
                    if ps is None:
                        raise exceptions.RouteWithoutPermissions("view function without permissions: " +
                                                                 self.name + '.' + f.__name__ + ': ' + request.url_rule.rule)

                    ps = ps.get(request.url_rule.rule, None)

                    if ps is None:
                        raise exceptions.RouteWithoutPermissions("cant find permissions for rule: " +
                                                                 self.name + '.' + f.__name__ + ': ' + request.url_rule.rule)

                    if method == 'OK':
                        json = request.json
                        if not ps['permissions'].check(json, *args, **kwargs):
                            raise exceptions.UnauthorizedUser()
                        ret = f(json, *args, **kwargs)
                    else:
                        if not ps['permissions'].check(*args, **kwargs):
                            raise exceptions.UnauthorizedUser()
                        ret = f(*args, **kwargs)

                except Exception as e:
                    if not g.debug:
                        type_, value_, traceback_ = sys.exc_info()
                        print('\n'.join(traceback.format_tb(traceback_)))
                        print(type_, value_)
                        if method == 'GET' or method == 'POST':
                            if getattr(e, 'redirect_to', None):
                                if method == 'GET':
                                    session['back_to'] = request.url
                                return redirect(e.redirect_to)
                            raise e
                        elif method == 'OK':
                            return jsonify(
                                {'data': {}, 'ok': False, 'error_code': 500, 'message': 'Server error'})
                    else:
                        raise e

                if method == 'GET' or method == 'POST':
                    return ret
                elif method == 'OK':
                    response = jsonify({'data': ret, 'ok': True, 'error_code': None})
                    return response

            if f.__name__ not in self.registered_functions:
                self.registered_functions[f.__name__] = {'func': wrapped_function, 'perm': {}, 'app': current_app}

            func = self.registered_functions[f.__name__]['func']
            if getattr(func, '_permissions', None) is None:
                setattr(func, '_permissions', {})

            func._permissions[self.url_prefix + rule] = \
                {'url_prefix': self.url_prefix, 'rule': rule, 'permissions': permissions}

            self.registered_functions[f.__name__]['perm'][self.url_prefix + rule] = permissions

            endpoint = options.pop("endpoint", f.__name__)

            self.add_url_rule(rule, endpoint, self.registered_functions[f.__name__]['func'], **options)

            return self.registered_functions[f.__name__]['func']

        return decorator


static_bp = PrBlueprint('static', __name__, static_folder='static')
index_bp = PrBlueprint('index', __name__, url_prefix='/')
auth_bp = PrBlueprint('auth', __name__, url_prefix='/auth')
admin_bp = PrBlueprint('admin', __name__, url_prefix='/admin')
user_bp = PrBlueprint('user', __name__, url_prefix='/user')
article_bp = PrBlueprint('article', __name__, url_prefix='/article')
filemanager_bp = PrBlueprint('filemanager', __name__, url_prefix='/filemanager')
company_bp = PrBlueprint('company', __name__, url_prefix='/company')
portal_bp = PrBlueprint('portal', __name__, url_prefix='/portal')
front_bp = PrBlueprint('front', __name__, url_prefix='/')
file_bp = PrBlueprint('file', __name__, url_prefix='/')
tools_bp = PrBlueprint('tools', __name__, url_prefix='/tools')
messenger_bp = PrBlueprint('messenger', __name__, url_prefix='/messenger')
tutorial_bp = PrBlueprint('tutorial', __name__, url_prefix='/tutorial')
