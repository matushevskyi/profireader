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
    def route(self, rule, **options):
        from functools import wraps
        from flask import request, render_template, session, redirect, url_for
        from ..models import exceptions
        if options and 'methods' in options and 'OK' in options['methods']:
            options['methods'][options['methods'].index('OK')] = 'POST'

        def decorator(f):

            # if not getattr(f, '__check_permissions__', False):
            #     raise exceptions.UnauthorizedAddress()

            @wraps(f)
            def wrapped_function(*args, **kwargs):
                method = request.method

                try:
                    ret = f(*args, **kwargs)
                    if not getattr(f, '__check_permissions__', False):
                        raise exceptions.UnauthorizedAddress()

                except exceptions.UnauthorizedAddress as e:
                    if method == 'GET':
                        return render_template('errors/general.html', message='Internal error')
                    elif method == 'POST':
                        return render_template('errors/general.html', message=e)
                    elif method == 'OK':
                        return render_template('errors/general.html', message=e)

                except exceptions.NotLoggedInUser as e:
                    if method == 'GET':
                        session['back_to'] = request.url
                        return redirect(url_for('auth.login_signup_endpoint'))
                    elif method == 'POST':
                        return render_template('errors/general.html', message=e)
                    elif method == 'OK':
                        return render_template('errors/general.html', message=e)

                except Exception as e:
                    if method == 'GET':
                        return render_template('errors/general.html', message=e)
                    elif method == 'POST':
                        return render_template('errors/general.html', message=e)
                    elif method == 'OK':
                        return render_template('errors/general.html', message=e)

                return ret

            endpoint = options.pop("endpoint", wrapped_function.__name__)
            self.add_url_rule(rule, endpoint, wrapped_function, **options)

            return wrapped_function

        return decorator


static_bp = PrOldBlueprint('static', __name__, static_folder='static')
index_bp = PrOldBlueprint('index', __name__)
auth_bp = PrOldBlueprint('auth', __name__)
admin_bp = PrOldBlueprint('admin', __name__)
user_bp = PrOldBlueprint('user', __name__)
article_bp = PrOldBlueprint('article', __name__)
filemanager_bp = PrOldBlueprint('filemanager', __name__)
image_editor_bp = PrOldBlueprint('image_editor', __name__)
company_bp = PrOldBlueprint('company', __name__)
portal_bp = PrOldBlueprint('portal', __name__)
front_bp = PrOldBlueprint('front', __name__)
file_bp = PrOldBlueprint('file', __name__)
exception_bp = PrOldBlueprint('exception', __name__)
tools_bp = PrOldBlueprint('tools', __name__)
# help_bp = PrOldBlueprint('help', __name__)
# reader_bp = PrOldBlueprint('reader', __name__)
messenger_bp = PrOldBlueprint('messenger', __name__)
new_bp = PrBlueprint('blablabla', __name__)
socket_bp = PrOldBlueprint('socket', __name__)
tutorial_bp = PrOldBlueprint('tutorial', __name__)
# reader_bp = Blueprint('reader', __name__)
