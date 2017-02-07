from flask import Blueprint


class PrOldBlueprint(Blueprint):
    declared_endpoints = {}

    def you_have_no_permission(self):
        raise Exception('You have no permission')

    def route(self, rule, **options):
        from .request_wrapers import ok
        def decorator(f):

            f.__endpoint__ = self.name
            f.__method__ = options['methods'] if 'methods' in options else ["GET"]
            if options and 'methods' in options and 'OK' in options['methods'] and self.name in self.declared_endpoints \
                    and f.__name__ in self.declared_endpoints[self.name]:
                options['methods'][options['methods'].index('OK')] = 'POST'
            if self.name in self.declared_endpoints and f.__name__ in self.declared_endpoints[self.name]:
                ret = self.declared_endpoints[self.name][f.__name__]
            else:
                ret = f
                if options and 'methods' in options and 'OK' in options['methods']:
                    options['methods'][options['methods'].index('OK')] = 'POST'
                    ret = ok(f)
                    # ret = function_profiler(ret)
                    self.declared_endpoints[self.name] = {}
                    self.declared_endpoints[self.name][ret.__name__] = ret
                else:
                    # ret = function_profiler(ret)
                    self.declared_endpoints[self.name] = {}
                    self.declared_endpoints[self.name][ret.__name__] = ret
            endpoint = options.pop("endpoint", ret.__name__)
            self.add_url_rule(rule, endpoint, ret, **options)

            return ret

        return decorator


class PrBlueprint(Blueprint):
    registered_functions = {}

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
            if not isinstance(permissions, list):
                permissions = [permissions]
            del options['permissions']
        else:
            raise exceptions.RouteWithoutPermissions()
            permissions = None

        def decorator(f):
            @wraps(f)
            def wrapped_function(*args, **kwargs):
                method = request.method
                if method == 'POST' and ok_method:
                    method = 'OK'
                hide_error = not (g.debug or g.testing)

                try:

                    def check_permissiosn(ps, *args, **kwargs):
                        if isinstance(ps, list):
                            for p in ps:
                                if check_permissiosn(p, *args, **kwargs):
                                    return True
                            return False
                        elif isinstance(ps, set):
                            for p in ps:
                                if not check_permissiosn(p, *args, **kwargs):
                                    return False
                            return True
                        else:
                            return ps(*args, **kwargs)

                    if request.url_rule.rule not in self.registered_functions[f.__name__]['perm']:
                        raise exceptions.RouteWithoutPermissions(
                            self.name + '.' + f.__name__ + ': ' + request.url_rule.rule)

                    ps = self.registered_functions[f.__name__]['perm'][request.url_rule.rule]

                    if not ps:
                        raise exceptions.RouteWithoutPermissions(
                            self.name + '.' + f.__name__ + ': ' + request.url_rule.rule)

                    if method == 'OK' or method == 'POST':
                        json = request.json
                        if not check_permissiosn(ps, json, *args, **kwargs):
                            raise exceptions.UnauthorizedUser()
                        ret = f(json, *args, **kwargs)
                    else:
                        if not check_permissiosn(ps, *args, **kwargs):
                            raise exceptions.UnauthorizedUser()
                        ret = f(*args, **kwargs)


                except exceptions.NotLoggedInUser as e:
                    if method == 'GET':
                        session['back_to'] = request.url
                        return redirect(url_for('auth.login_signup_endpoint'))
                    elif method == 'POST':
                        return redirect(url_for('auth.login_signup_endpoint'))
                    elif method == 'OK':
                        return jsonify(
                            {'data': {}, 'ok': False, 'error_code': exceptions.NotLoggedInUser.__name__})

                # except Exception as e:
                #     if method == 'GET':
                #         return render_template('errors/general.html', message='Internal error' if hide_error else e)
                #     elif method == 'POST':
                #         return render_template('errors/general.html', message='Internal error' if hide_error else e)
                #     elif method == 'OK':
                #         return jsonify({'data': {} if hide_error else traceback.extract_stack(), 'ok': False,
                #                         'error_code': e if hide_error else type(e).__name__})

                if method == 'GET':
                    return ret
                elif method == 'POST':
                    return ret
                elif method == 'OK':
                    return jsonify({'data': ret, 'ok': True, 'error_code': 'NO_ERROR'})

            if f.__name__ not in self.registered_functions:
                self.registered_functions[f.__name__] = {'func': wrapped_function, 'perm': [], 'app': current_app}

            self.registered_functions[f.__name__]['perm'][self.url_prefix + rule] = permissions

            endpoint = options.pop("endpoint", f.__name__)
            self.add_url_rule(rule, endpoint, self.registered_functions[f.__name__]['func'], **options)

            return self.registered_functions[f.__name__]['func']

        return decorator


static_bp = PrOldBlueprint('static', __name__, static_folder='static')
index_bp = PrOldBlueprint('index', __name__)
auth_bp = PrOldBlueprint('auth', __name__)
admin_bp = PrOldBlueprint('admin', __name__)
user_bp = PrOldBlueprint('user', __name__)
article_bp = PrBlueprint('article', __name__)
filemanager_bp = PrOldBlueprint('filemanager', __name__)
image_editor_bp = PrOldBlueprint('image_editor', __name__)
company_bp = PrBlueprint('company', __name__, url_prefix='/company')
portal_bp = PrOldBlueprint('portal', __name__)
front_bp = PrOldBlueprint('front', __name__)
file_bp = PrOldBlueprint('file', __name__)
exception_bp = PrOldBlueprint('exception', __name__)
tools_bp = PrOldBlueprint('tools', __name__)
# help_bp = PrOldBlueprint('help', __name__)
# reader_bp = PrOldBlueprint('reader', __name__)
messenger_bp = PrBlueprint('messenger', __name__, url_prefix='/messenger')
socket_bp = PrOldBlueprint('socket', __name__)
tutorial_bp = PrOldBlueprint('tutorial', __name__)
# reader_bp = Blueprint('reader', __name__)
