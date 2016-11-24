from .blueprints_declaration import auth_bp
from flask import g, request, url_for, render_template, flash, current_app, session
from ..constants.SOCIAL_NETWORKS import DB_FIELDS, SOC_NET_FIELDS, \
    SOC_NET_FIELDS_SHORT
from flask.ext.login import current_user, login_required
from urllib.parse import quote
from ..models.users import User
from tools.db_utils import db
import re
from .request_wrapers import check_right
from authomatic.adapters import WerkzeugAdapter
from flask import redirect, make_response
from flask.ext.login import login_user
from ..constants.SOCIAL_NETWORKS import SOC_NET_NONE
from ..constants.UNCATEGORIZED import AVATAR_SIZE, AVATAR_SMALL_SIZE
from .. import utils
from ..models.rights import AllowAll
from ..models.portal import Portal
from ..models.messenger import Socket
import sys
import string
#


def set_after_logination_params():
    back_to = g.req('back_to')
    if back_to:
        session['back_to'] = back_to
    portal_id = g.req('portal_id')
    if portal_id:
        session['portal_id'] = portal_id


def check_after_logination_params(user):
    if session.get('portal_id'):
        portal = Portal.get(session.get('portal_id'), returnNoneIfNotExists=True)
        if portal:
            portal.subscribe_user(user)
            session.pop('portal_id')
    if session.get('back_to'):
        session.pop('back_to')
        return session['back_to']
    else:
        return False

def get_after_logination_params():
    ret = {}
    if session.get('portal_id'):
        ret['portal_id'] = session['portal_id']
        session.pop('portal_id')
    if session.get('back_to'):
        ret['back_to'] = session['back_to']
        session.pop('back_to')
    return ret

@auth_bp.route('/login_signup/', methods=['GET'])
@check_right(AllowAll)
def login_signup_endpoint():
    if current_user.is_authenticated():
        back_to = check_after_logination_params(current_user)
        return redirect(back_to if back_to else url_for('index.index'))
    else:
        set_after_logination_params()
        return render_template('auth/login_signup.html', login_signup=request.args.get('login_signup', 'login'))


@auth_bp.route('/login_signup/', methods=['OK'])
@check_right(AllowAll)
def signup(json_data):
    action = g.req('action', allowed=['validate', 'save'])

    params = utils.filter_json(json_data, 'first_name,last_name,email,password,password_confirmation')
    params['address_email'] = params['email']
    del params['email']
    new_user = User(**params)

    if action == 'validate':
        return new_user.validate(True)
    else:
        new_user.set_password_hash()
        new_user.save()
        g.db.commit()
        new_user.generate_confirmation_token(get_after_logination_params()).save()
        Socket.send_greeting([new_user])
        g.db.commit()

        return {}



@auth_bp.route('/login/', methods=['OK'])
@check_right(AllowAll)
def login(json_data):
    email = json_data.get('email', '')
    password = json_data.get('password', '')

    user = g.db.query(User).filter(User.address_email == email).first()

    if user and user.banned:
        return {'error': 'You can not be logged in. Please contact the Profireader administration'}
    elif user and not user.email_confirmed:
        return {'error': 'You email is unconfirmed. Please confirm your email'}
    elif not user or not user.verify_password(password):
        return {'error': 'Email or password is wrong'}
    else:
        user.login()
        return {'back_to': check_after_logination_params(user)}


@auth_bp.route('/email_confirmation/', methods=['GET'])
@auth_bp.route('/email_confirmation/<string:token>/', methods=['GET'])
@check_right(AllowAll)
def email_confirmation(token=None):
    set_after_logination_params()
    if not token:
        return render_template("auth/confirm_email.html", email='')

    user = db(User, email_conf_token=token).first()

    if not user:
        return render_template("auth/confirm_email.html", email='',
                               wrong_email_confirmation_token_entered=True)
    elif not user.confirm_email():
        return render_template("auth/confirm_email.html", email=user.address_email,
                               wrong_email_confirmation_token_entered=True)
    else:
        User.logout()
        user.save()
        g.db.commit()
        user.login()
        back_to = check_after_logination_params(user)
        return redirect(back_to if back_to else url_for('index.welcome'))


@auth_bp.route('request_new_email_confirmation_token/', methods=["OK"])
@check_right(AllowAll)
def request_new_email_confirmation_token(json_data):
    from ..constants import REGEXP
    email = json_data.get('email', '')

    if not re.match(REGEXP.EMAIL, email):
        return {'error': 'Please enter correct email'}
    else:
        user = db(User, address_email=email).first()
        if user:
            if user.email_confirmed:
                return {'error': 'You email is already confirmed'}
            else:
                user.generate_confirmation_token(get_after_logination_params()).save()
                return {}
        else:
            return {'error': 'User with this email is not registered'}


@auth_bp.route('tos/', methods=['OK'])
@check_right(AllowAll)
def tos(json):
    if json.get('accept', False):
        current_user.tos = True
        current_user.save()
        return current_user.tos
    else:
        return {'error': 'tos acceptation error'}



# TODO: YG by OZ:
# @auth_bp.route('//', methods=['POST'])
@auth_bp.route('/login_signup/<soc_network_name>', methods=['GET', 'POST'])
@check_right(AllowAll)
def login_signup_soc_network(soc_network_name):
    # TODO: fix it!
    portal_id = session.get('portal_id')
    back_to = session.get('back_to')
    response = make_response()

    result = g.authomatic.login(WerkzeugAdapter(request, response), soc_network_name)

    if result:
        if result.user:
            result.user.update()
            result_user = result.user
            if result_user.email is None:
                return render_template('error.html',
                                       error="You haven't confirm email bound to your soc-network account yet. ")
            # db_fields = DB_FIELDS[soc_network_names[-1]]
            # user = g.db.query(User).filter(getattr(User, db_fields['id']) == result_user.id).first()

            user = g.db.query(User).filter(getattr(User, soc_network_name + '_id') == result_user.email).first()

            # we have already this user registered
            if not user:
                user = g.db.query(User).filter(User.address_email == result_user.email).first()
                if user:
                    setattr(user, soc_network_name + '_id', result_user.id)
                    user.email_confirmed = True
                    user.save()

            # ok, new user
            if not user:
                user = User(registered_via=soc_network_name, first_name=result_user.first_name,
                            last_name=result_user.last_name, address_email=result_user.email)
                setattr(user, soc_network_name + '_id', result_user.id)
                user.email_confirmed = True
                user.avatar_selected_preset = 'gravatar'
                g.db.add(user)
                user.save()
                Socket.send_greeting([user])

            if user:
                User.logout()
                user.login()
                back_to = check_after_logination_params(user)
                return redirect(back_to if back_to else url_for('index.index'))
            else:
                return render_template('error.html', error='cant login/signup user')
        elif result.error:
            return render_template('error.html', debug=result.error)

    return response



@auth_bp.route('/logout/', methods=['GET'])
@login_required
@check_right(AllowAll)
def logout():
    User.logout()
    return redirect(url_for('index.index'))


@auth_bp.route('/request_new_password/', methods=['GET'])
@check_right(AllowAll)
def request_new_reset_password_token():
    return render_template("auth/request_new_password.html")


@auth_bp.route('/request_new_password/', methods=["OK"])
@check_right(AllowAll)
def request_new_reset_password_token_load(json_data):
    from ..constants import REGEXP
    email = json_data.get('email', '')

    if not re.match(REGEXP.EMAIL, email):
        return {'error': 'Please enter correct email'}
    else:
        user = db(User, address_email=email).first()
        if user:
            user.generate_pass_reset_token().save()
            return {}
        else:
            return {'error': 'User with this email is not registered'}


@auth_bp.route('/reset_password/<string:token>/', methods=['GET'])
@check_right(AllowAll)
def reset_password(token):
    return render_template("auth/reset_password.html",
                           reset_pass_user=db(User, pass_reset_token=token).first())


@auth_bp.route('/reset_password/<string:token>/', methods=['OK'])
@check_right(AllowAll)
def reset_password_load(json_data, token):
    user = db(User, pass_reset_token=token).first()
    if user:
        user.password = json_data['password']
        user.password_confirmation = json_data['password_confirmation']
        validation = user.validate(False)
        if validation['errors']:
            return {'error': list(validation['errors'].values())[0]}
        elif not user.reset_password():
            return {'error': 'cant set new password'}
        else:
            User.logout()
            user.login()
            back_to = check_after_logination_params(user)
            return {'back_to': back_to}
    else:
        return {'error': 'Wrong token. or token outdated'}

