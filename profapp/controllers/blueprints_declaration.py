from flask import Blueprint, g
from utils.db_utils import db
from functools import wraps



class PrBlueprint(Blueprint):

    bluprints = {}
    def you_have_no_permission(self):
        raise Exception('You have no permission')


    def route(self, rule, **options):
        from .request_wrapers import ok, function_profiler
        def decorator(f):
            f.__endpoint__ = self.name
            f.__method__ = options['methods'] if 'methods' in options else ["GET"]
            if options and 'methods' in options and 'OK' in options['methods'] and self.name in self.bluprints and f.__name__ in self.bluprints[self.name]:
                index = options['methods'].index('OK')
                options['methods'][index] = 'POST'
            if self.name in self.bluprints and f.__name__ in self.bluprints[self.name]:
                ret = self.bluprints[self.name][f.__name__]
            else:
                ret = f
                if options and 'methods' in options and 'OK' in options['methods']:
                    index = options['methods'].index('OK')
                    options['methods'][index] = 'POST'
                    ret = ok(f)
                    ret = function_profiler(ret)
                    self.bluprints[self.name] = {}
                    self.bluprints[self.name][ret.__name__] = ret
                else:
                    ret = function_profiler(ret)
                    self.bluprints[self.name] = {}
                    self.bluprints[self.name][ret.__name__] = ret
            endpoint = options.pop("endpoint", ret.__name__)
            self.add_url_rule(rule, endpoint, ret, **options)
            return ret
        return decorator

print('blueprint declaration')
static_bp = PrBlueprint('static', __name__, static_folder='static')
general_bp = PrBlueprint('general', __name__)
auth_bp = PrBlueprint('auth', __name__)
admin_bp = PrBlueprint('admin', __name__)
user_bp = PrBlueprint('user', __name__)
article_bp = PrBlueprint('article', __name__)
filemanager_bp = PrBlueprint('filemanager', __name__)
image_editor_bp = PrBlueprint('image_editor', __name__)
company_bp = PrBlueprint('company', __name__)
portal_bp = PrBlueprint('portal', __name__)
front_bp = PrBlueprint('front', __name__)
file_bp = PrBlueprint('file', __name__)
exception_bp = PrBlueprint('exception', __name__)
tools_bp = PrBlueprint('tools', __name__)
help_bp = PrBlueprint('help', __name__)
reader_bp = PrBlueprint('reader', __name__)
messenger_bp = PrBlueprint('messenger', __name__)
tutorial_bp = PrBlueprint('tutorial', __name__)
# reader_bp = Blueprint('reader', __name__)




