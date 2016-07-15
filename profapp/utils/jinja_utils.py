from flask import Flask, g, request, current_app, session
import jinja2
from jinja2 import Markup, escape
import datetime
from ..models.translate import TranslateTemplate
import re
import json
from ..models.tools import HtmlHelper
from ..models.pr_base import MLStripper
from .. import utils
from .. import Config
from ..models.config import Config as ModelConfig


def translate_phrase_or_html(context, phrase, dictionary=None, allow_html=''):
    template = context.name
    translated = TranslateTemplate.getTranslate(template, phrase, None, allow_html)
    r = re.compile("%\\(([^)]*)\\)s")

    def getFromContext(context, indexes, default):
        d = context
        for i in indexes:
            if i in d:
                d = d[i]
            else:
                return default
        return d

    def replaceinphrase(match):
        indexes = match.group(1).split('.')
        return str(getFromContext(context if dictionary is None else dictionary, indexes, match.group(1)))

    return r.sub(replaceinphrase, translated)


def get_url_adapter():
    from flask import globals as flask_globals
    appctx = flask_globals._app_ctx_stack.top
    reqctx = flask_globals._request_ctx_stack.top
    if reqctx is not None:
        url_adapter = reqctx.url_adapter
    else:
        url_adapter = appctx.url_adapter
    return url_adapter


# TODO: OZ by OZ: add kwargs just like in url_for
def raw_url_for(endpoint):
    url_adapter = get_url_adapter()

    rules = url_adapter.map._rules_by_endpoint.get(endpoint, ())

    if len(rules) < 1:
        raise Exception('You requsted url for endpoint `%s` but no endpoint found' % (endpoint,))

    rules_simplified = [re.compile('<[^:]*:').sub('<', rule.rule) for rule in rules]

    return "function (dict, host) { return find_and_build_url_for_endpoint(dict, %s, host); }" % (json.dumps(rules_simplified))
    # \
    #        " { var ret = '" + ret + "'; " \
    #                                                " for (prop in dict) ret = ret.replace('<'+prop+'>',dict[prop]); return ret; }"


def pre(value):
    res = []
    for k in dir(value):
        res.append('%r %r\n' % (k, getattr(value, k)))
    return '<pre>' + '\n'.join(res) + '</pre>'


def translates(template):
    phrases = g.db.query(TranslateTemplate).filter_by(template=template).all()
    ret = {}
    for ph in phrases:
        tim = ph.ac_tm.timestamp() if ph.ac_tm else ''
        html_or_text = getattr(ph, g.lang)
        html_or_text = MLStripper().strip_tags(html_or_text) if ph.allow_html == '' else html_or_text
        ret[ph.name] = {'lang': html_or_text, 'time': tim, 'allow_html': ph.allow_html}
    return json.dumps(ret)


def prImageUrl(url):
    from . import static_address
    return Markup(' src="' + static_address('images/0.gif') +
                  '" style="background-position: center; background-size: contain; background-repeat: no-repeat; '
                  'background-image: url(\'%s\')" ' % (url,))

# TODO: OZ by OZ: remove this function
def prImage(id=None, if_no_image=None):
    from . import static_address
    noimage_url = if_no_image if if_no_image else static_address('images/no_image.png')
    return prImageUrl((utils.fileUrl(id, False, noimage_url)) if id else noimage_url)


def config_variables():
    variables = g.db.query(ModelConfig).filter_by(server_side=1).all()
    ret = {}
    for variable in variables:
        var_id = variable.id
        if variable.type == 'int':
            ret[var_id] = '%s' % (int(variable.value),)
        elif variable.type == 'bool':
            ret[var_id] = 'false' if int(variable.value) == 0 else 'true'
        elif variable.type == 'float':
            ret[var_id] = '%s' % (float(variable.value))
        elif variable.type == 'timestamp':
            ret[var_id] = 'new Date(%s)' % (int(variable.value))
        else:
            ret[var_id] = '\'' + variable.value.replace('\\', '\\\\').replace('\n', '\\n').replace('\'', '\\\'') + '\''

    return "<script>\n_LANG = '" + g.lang + "'; \nConfig = {};\n" + ''.join(
        [("Config['%s']=%s;\n" % (var_id, ret[var_id])) for var_id in ret]) + \
           "static_address = function (relative_file_name) {return '//static." + \
           Config.MAIN_DOMAIN + "/static/' + relative_file_name; };\n" \
                                "MAIN_DOMAIN = '" + Config.MAIN_DOMAIN + "';\n</script>"


@jinja2.contextfunction
def translate_phrase(context, phrase, dictionary=None):
    return MLStripper().strip_tags(translate_phrase_or_html(context, phrase, dictionary, ''))


@jinja2.contextfunction
def translate_html(context, phrase, dictionary=None):
    return Markup(translate_phrase_or_html(context, phrase, dictionary, '*'))

def static_address_html(relative_file_name):
    return Markup(utils.static_address(relative_file_name))


@jinja2.contextfunction
def pr_help_tooltip(context, phrase, placement='bottom', trigger='mouseenter',
                    classes='glyphicon glyphicon-question-sign'):
    return Markup(
        '<span popover-placement="' + placement + '" popover-trigger="' + trigger + '" class="' + classes +
        '" uib-popover-html="\'' + HtmlHelper.quoteattr(
            translate_phrase_or_html(context, 'help tooltip ' + phrase, None, '*')) + '\'"></span>')


def moment(value, out_format=None):
    if isinstance(value, datetime.datetime):
        print(out_format)
        value = value.isoformat(' ') + ' GMT'
        return Markup(
            "<script> document.write(moment(new Date('{}')).format('{}')) </script><noscript>{}</noscript>".format(
                value, out_format if out_format else 'dddd, LL (HH:mm)', value))
    elif isinstance(value, datetime.date):
        print(2)
        value = value.strftime('%Y-%m-%d')
        return Markup(
            "<script> document.write(moment('{}').format('{}')) </script><noscript>{}</noscript>".format(
                value, out_format if out_format else 'dddd, LL', value))
    else:
        print(3)
        return Markup(
            "<script> document.write(moment(new Date('{}')).format('{}')) </script><noscript>{}</noscript>".format(
                value, out_format if out_format else 'dddd, LL (HH:mm)', value))


@jinja2.contextfunction
def nl2br(value):
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    result = Markup(result)
    return result


def raise_helper(msg):
    raise Exception(msg)


def update_jinja_engine(app):
    app.jinja_env.globals.update(raw_url_for=raw_url_for)
    app.jinja_env.globals.update(pre=pre)
    app.jinja_env.globals.update(utils=utils)
    app.jinja_env.globals.update(translates=translates)
    app.jinja_env.globals.update(fileUrl=utils.fileUrl)
    app.jinja_env.globals.update(prImage=prImage)
    app.jinja_env.globals.update(prImageUrl=prImageUrl)
    app.jinja_env.globals.update(config_variables=config_variables)
    app.jinja_env.globals.update(_=translate_phrase)
    app.jinja_env.globals.update(__=translate_html)
    app.jinja_env.globals.update(moment=moment)
    app.jinja_env.globals.update(static_address=static_address_html)
    app.jinja_env.globals.update(MAIN_DOMAIN=Config.MAIN_DOMAIN)
    app.jinja_env.globals['raise'] = raise_helper
    app.jinja_env.globals.update(tinymce_format_groups=HtmlHelper.tinymce_format_groups)
    app.jinja_env.globals.update(pr_help_tooltip=pr_help_tooltip)

    app.jinja_env.filters['nl2br'] = nl2br
