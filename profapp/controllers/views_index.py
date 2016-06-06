from flask import render_template, request, session, redirect, url_for, g
from .blueprints_declaration import general_bp
from ..models.portal import Portal, UserPortalReader
from ..models.pr_base import Search, PRBase
from utils.pr_email import email_send
from utils.db_utils import db
from .request_wrapers import check_right
from ..models.rights import AllowAll
from .. import utils

@general_bp.route('help/')
@check_right(AllowAll)
def help():
    email = None
    if g.user:
        email = g.user.profireader_email
    return render_template('help.html', data={'email':email})


@general_bp.route('')
@check_right(AllowAll)
def index():
    if g.user and g.user.is_authenticated() and getattr(g.user, 'tos', False):
        return redirect(url_for('reader.list_reader'))
    return render_template('general/index.html')


@general_bp.route('portals_list/', methods=['GET'])
@check_right(AllowAll)
def portals_list():
    return render_template('general/portals_list.html')


@general_bp.route('portals_list/', methods=['OK'])
@check_right(AllowAll)
def portals_list_load(json):
    ret, page, page2 = Search().search(
        {'class': Portal,
         'filter':(~Portal.id.in_(db(UserPortalReader.portal_id).filter(UserPortalReader.user_id==g.user.id).all())) if g.user else None,
         'return_fields': 'default_dict'},
          page=1, search_text=json.get('text'), pagination=True, items_per_page=5 * json.get('next_page'))
    return {'list_portals':[utils.merge_dicts(p, {'subscribed': True if UserPortalReader.get(portal_id=p_id) else
    False})
            for p_id, p in ret.items()], 'end': True if page == 1 or page == 0 else False}


@general_bp.route('subscribe/<string:portal_id>', methods=['GET'])
@check_right(AllowAll)
def auth_before_subscribe_to_portal(portal_id):
    session['portal_id'] = portal_id
    return redirect(url_for('auth.login_signup_endpoint', login_signup='login'))

# YG it`s not used but it will change in future
@general_bp.route('send_email_create_portal/')
@check_right(AllowAll)
def send_email_create_portal():
    return render_template('general/send_email_create_portal.html')


@general_bp.route('send_email', methods=['POST'])
@check_right(AllowAll)
def send_email():
    return email_send(**{name: str(val) for name, val in request.form.items()})
