from flask import Flask, g, request, current_app, session, url_for, jsonify
import jinja2
from jinja2 import Markup, escape
import datetime
from ..models.translate import TranslateTemplate
import re
import json
from ..models.tools import HtmlHelper
from .. import utils
from .. import Config
from config import secret_data
from main_domain import MAIN_DOMAIN
from ..models.config import Config as ModelConfig
import hashlib
from profapp.models.third.google_analytics_management import PortalAnalytics


def link(href_placeholder, text_placeholder, placeholder_is_text=False):
    return "<a href=\"%(" + href_placeholder + ")s\">" + text_placeholder + "</a>" \
        if placeholder_is_text else \
        "<a href=\"%(" + href_placeholder + ")s\">%(" + text_placeholder + ")s</a>"


def link_external(href_placeholder='portal.host', text_placeholder='portal.name', url_prefix='//'):
    return "<a class=\"external_link\" target=\"blank_\" href=\"" + url_prefix + "%(" + href_placeholder + ")s\">%(" + \
           text_placeholder + ")s<span class=\"fa fa-external-link pr-external-link\"></span></a>"


def link_company_profile():
    return link('url_company_profile', 'company.name')


def link_user_profile():
    return link('url_profile_from_user', 'from_user.full_name')


def grid_url(id, endpoint, **kwargs):
    return url_for(endpoint, **kwargs) + '#guuid=' + id


def translate_phrase_or_html(context, phrase, dictionary=None, allow_html='', phrase_comment=None, phrase_default=None):
    return TranslateTemplate.translate_and_substitute(context.name, phrase,
                                                      context if dictionary is None else dictionary,
                                                      language=None,
                                                      url=None, allow_html=allow_html,
                                                      phrase_comment=phrase_comment, phrase_default=phrase_default)


def get_url_adapter():
    from flask import globals as flask_globals
    appctx = flask_globals._app_ctx_stack.top
    reqctx = flask_globals._request_ctx_stack.top
    if reqctx is not None:
        url_adapter = reqctx.url_adapter
    else:
        url_adapter = appctx.url_adapter
    return url_adapter


def get_rules_simplified(endpoint, **kwargs):
    url_adapter = get_url_adapter()

    rules = url_adapter.map._rules_by_endpoint.get(endpoint, ())

    if len(rules) < 1:
        raise Exception('You requsted url for endpoint `%s` but no endpoint found' % (endpoint,))

    rules_simplified = []
    for rule in rules:
        r = re.compile('<[^:]*:').sub('<', rule.rule)
        for (k, v) in kwargs.items():
            r = re.compile('<' + k + '>').sub(v, r)
        rules_simplified.append(r)

    return rules_simplified


# TODO: OZ by OZ: add kwargs just like in url_for
def grid_raw_url_for(endpoint, **kwargs):
    rules_simplified = get_rules_simplified(endpoint, **kwargs)

    return "function (id, dict, host) { return find_and_build_url_for_endpoint(dict?dict:$scope, %s, host) + '#guuid=' + id; }" % (
        json.dumps(rules_simplified, ))


def raw_url_for(endpoint, **kwargs):
    rules_simplified = get_rules_simplified(endpoint, **kwargs)

    return "function (dict, host) { return find_and_build_url_for_endpoint(dict?dict:$scope, %s, host); }" % (
        json.dumps(rules_simplified))


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
        html_or_text = utils.strip_tags(html_or_text) if ph.allow_html == '' else html_or_text
        ret[ph.name] = {'lang': html_or_text, 'time': tim, 'allow_html': ph.allow_html}
    return json.dumps(ret)


def prImageUrl(url, position='center'):
    from . import static_address
    return Markup(' src="' + static_address('images/0.gif') +
                  '" style="background-position: ' + position + '; background-size: contain; background-repeat: no-repeat; '
                                                                'background-image: url(\'%s\')" ' % (url,))


# TODO: OZ by OZ: remove this function
def prImage(id=None, if_no_image=None, position='center'):
    from . import static_address
    noimage_url = if_no_image if if_no_image else static_address('images/no_image.png')
    return prImageUrl((utils.fileUrl(id, False, noimage_url)) if id else noimage_url, position=position)


def config_variables():
    variables = g.db.query(ModelConfig).filter_by(client_side=1).all()
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
def translate_phrase(context, phrase, dictionary=None, phrase_default=None, phrase_comment=None):
    return utils.strip_tags(translate_phrase_or_html(context, phrase, dictionary, '', phrase_default=phrase_default,
                                                     phrase_comment=phrase_comment))


@jinja2.contextfunction
def translate_html(context, phrase, dictionary=None, phrase_default=None, phrase_comment=None):
    return Markup(translate_phrase_or_html(context, phrase, dictionary, '*', phrase_default=phrase_default,
                                           phrase_comment=phrase_comment))


def google_analytics(portal, analytics: PortalAnalytics):
    from profapp.models.third.google_analytics_management import CUSTOM_DIMENSION, CUSTOM_METRIC
    if not portal['google_analytics_web_property_id']:
        return ''
    analytics = json.dumps({
        'dimension' + str(portal['google_analytics_dimensions'][
                              CUSTOM_DIMENSION['user_type']]): 'Identified' if g.user else 'Anonymous',
        'dimension' + str(portal['google_analytics_dimensions'][
                              CUSTOM_DIMENSION['company_id']]): analytics.company_id,
        'dimension' + str(portal['google_analytics_dimensions'][
                              CUSTOM_DIMENSION['page_type']]): analytics.page_type,
        'dimension' + str(portal['google_analytics_dimensions'][
                              CUSTOM_DIMENSION['publication_visibility']]): analytics.publication_visibility,
        'dimension' + str(portal['google_analytics_dimensions'][
                              CUSTOM_DIMENSION['publication_reached']]): analytics.publication_reached,
        'metric' + str(portal['google_analytics_metrics'][
                           CUSTOM_METRIC['income']]): analytics.income,
    })
    return Markup("""<!-- Google Analytics -->
<script>
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

ga('create', '""" + portal['google_analytics_web_property_id'] + """', 'auto');
ga('set', """ + analytics + """);
ga('send', 'pageview');
</script>
<!-- End Google Analytics -->""")


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
        value = value.isoformat(' ')
        return Markup(
            "<script>document.write(moment.utc('{}', 'YYYY-MM-DD HH:mm:ss GMT').local().format('{}')) </script><noscript>{} GMT</noscript>".format(
                value, out_format if out_format else 'dddd, LL (HH:mm)', value))
    elif isinstance(value, datetime.date):
        value = value.strftime('%Y-%m-%d')
        return Markup(
            "<script>document.write(moment('{}', 'YYYY-MM-DD').format('{}')) </script><noscript>{}</noscript>".format(
                value, out_format if out_format else 'dddd, LL', value))
    else:
        return Markup(
            "<script>document.write(moment.utc('{}').local().format('{}')) </script><noscript>{}</noscript>".format(
                value, out_format if out_format else 'dddd, LL (HH:mm)', value))


@jinja2.contextfunction
def date(value):
    return Markup(value.strftime('%Y-%m-%d'))


@jinja2.contextfunction
def timestamp(value):
    return Markup(value.strftime("%Y-%m-%d %H:%M:%S"))


@jinja2.contextfunction
def nl2br(value):
    _paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', Markup('<br>\n'))
                          for p in _paragraph_re.split(escape(value)))
    result = Markup(result)
    return result


@jinja2.contextfunction
def nl2space(value):
    # _spaces = re.compile(r'(?:\r\n|\r|\n){2,}')
    return Markup(value.replace('\n', ' '))


@jinja2.contextfunction
def strip_tags(value):
    # _spaces = re.compile(r'(?:\r\n|\r|\n){2,}')
    return Markup(utils.strip_tags(value))


@jinja2.contextfunction
def highlighted(val_dict_or_obj, key):
    highn = key + '_highlighted'
    if isinstance(val_dict_or_obj, dict):
        result = val_dict_or_obj[highn] if highn in val_dict_or_obj else val_dict_or_obj[key]
    else:
        result = getattr(val_dict_or_obj, highn) if hasattr(val_dict_or_obj, highn) else getattr(val_dict_or_obj, key)
    return Markup(result)


def raise_helper(msg):
    raise Exception(msg)


from werkzeug.routing import RequestRedirect, MethodNotAllowed, NotFound


def get_view_function(url, method='GET'):
    """Match a url and return the view and arguments
    it will be called with, or None if there is no view.
    """
    adapter = current_app.url_map.bind(None)

    try:
        match = adapter.match(url, method=method)
    except RequestRedirect as e:
        # recursively match redirects
        return get_view_function(e.new_url, method)
    except (MethodNotAllowed, NotFound):
        # no match
        return None

    try:
        # return the view function and arguments
        return current_app.view_functions[match[0]], match[1]
    except KeyError:
        # no view is associated with the endpoint
        return None


def _url_permitted(endpoint, dictionary={}):
    permissions = getattr(current_app.view_functions[endpoint], '_permissions', None)

    if permissions is None:
        raise Exception('url_permitted: View function for endpoint `{}` without without permissions'.format(endpoint))

    for ind, permission in permissions.items():

        matched = {}
        for d in dictionary:
            if re.match(r'.*<([^:]+(\([^()]+\))?:)?' + d + '>.*', permission['rule']):
                matched[d] = dictionary[d]
        if matched == dictionary:
            return url_for(endpoint, **dictionary) if permission['permissions'].check(**dictionary) else False

    raise Exception(
        'url_permitted: Cant find any matched rule at endpoint `{}` for passed dictionary {}'.format(endpoint,
                                                                                                     dictionary))


def update_jinja_engine(app):
    def tbvm():
        return ' target="_blank" ' if g.user and g.user.id in ['561e3eaf-2188-4001-b542-e607537567b2'] else ''

    app.jinja_env.globals.update(raw_url_for=raw_url_for)
    app.jinja_env.globals.update(grid_raw_url_for=grid_raw_url_for)
    app.jinja_env.globals.update(pre=pre)
    app.jinja_env.globals.update(utils=utils)
    app.jinja_env.globals.update(translates=translates)
    app.jinja_env.globals.update(fileUrl=utils.fileUrl)
    app.jinja_env.globals.update(prImage=prImage)
    app.jinja_env.globals.update(prImageUrl=prImageUrl)
    app.jinja_env.globals.update(config_variables=config_variables)
    app.jinja_env.globals.update(secret_data=secret_data)
    app.jinja_env.globals.update(_=translate_phrase)
    app.jinja_env.globals.update(__=translate_html)
    app.jinja_env.globals.update(google_analytics=google_analytics)
    app.jinja_env.globals.update(moment=moment)
    app.jinja_env.globals.update(static_address=static_address_html)
    app.jinja_env.globals.update(MAIN_DOMAIN=Config.MAIN_DOMAIN)
    app.jinja_env.globals['raise'] = raise_helper
    app.jinja_env.globals.update(tinymce_format_groups=HtmlHelper.tinymce_format_groups)
    app.jinja_env.globals.update(pr_help_tooltip=pr_help_tooltip)
    app.jinja_env.globals.update(tbvm=tbvm)
    app.jinja_env.globals.update(_url_permitted=_url_permitted)
    app.jinja_env.globals.update(
        _URL_JOIN=lambda: '//' + MAIN_DOMAIN + '/auth/login_signup/?login_signup=signup&portal_id=' + g.portal_id if g.portal_id else None)
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['nl2space'] = nl2space
    app.jinja_env.filters['strip_tags'] = strip_tags
    app.jinja_env.filters['highlighted'] = highlighted
    app.jinja_env.filters['timestamp'] = timestamp
    app.jinja_env.filters['date'] = date

    macro = ("""{% macro if_url_permitted(endpoint) %}
{% if _url_permitted(endpoint, kwargs) %}
{{ caller(_url_permitted(endpoint, kwargs)) }}
{% endif %}
{% endmacro %}""")

    macro_template = app.jinja_env.from_string(macro)
    app.jinja_env.globals['if_url_permitted'] = macro_template.module.if_url_permitted
