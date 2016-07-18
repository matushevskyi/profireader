from .blueprints_declaration import auth_bp
from flask import g, request, url_for, render_template, flash, current_app, session
from ..constants.SOCIAL_NETWORKS import DB_FIELDS, SOC_NET_FIELDS, \
    SOC_NET_FIELDS_SHORT
from flask.ext.login import current_user, login_required
from urllib.parse import quote
from ..models.users import User
from utils.db_utils import db
import re
from .request_wrapers import check_right
from authomatic.adapters import WerkzeugAdapter
from flask import redirect, make_response
from flask.ext.login import login_user
from ..constants.SOCIAL_NETWORKS import SOC_NET_NONE
from ..constants.UNCATEGORIZED import AVATAR_SIZE, AVATAR_SMALL_SIZE
from ..utils.redirect_url import redirect_url
from utils.pr_email import SendEmail
from ..models.rights import AllowAll
from ..models.portal import Portal
import sys


def login_signup_general(*soc_network_names):
    portal_id = session.get('portal_id')
    back_to = session.get('back_to')
    response = make_response()
    registred_via_soc = False
    logged_via_soc = list(filter(lambda x: x != 'profireader', soc_network_names))[0] \
        if len(soc_network_names) > 1 else 'profireader'

    try:
        result = g.authomatic.login(WerkzeugAdapter(request, response), soc_network_names[-1])
        if result:
            if result.user:
                result.user.update()
                result_user = result.user
                if result_user.email is None:
                    flash("you haven't confirm email bound to your soc-network account yet. "
                          "Please confirm email first or choose another way of authentication.")
                    # redirect(url_for('auth.login_signup_endpoint') + '?login_signup=login')
                    redirect(redirect_url())
                db_fields = DB_FIELDS[soc_network_names[-1]]
                # user = g.db.query(User).filter(getattr(User, db_fields['id']) == result_user.id).first()

                user = g.db.query(User).filter(getattr(User, db_fields['email']) == result_user.email).first()

                if not user:
                    user = g.db.query(User).filter(User.address_email == result_user.email).first()
                    ind = False

                    if not user:
                        ind = True
                        user = User()

                    for elem in SOC_NET_FIELDS:
                        setattr(user, db_fields[elem], getattr(result_user, elem))
                    registred_via_soc = len(soc_network_names) > 1

                    if ind:  # ToDo (AA): introduce field signup_via instead.
                        # Todo (AA): If signed_up not via profireader then...
                        db_fields_profireader = DB_FIELDS['profireader']
                        for elem in SOC_NET_FIELDS_SHORT:
                            setattr(user, db_fields_profireader[elem], getattr(result_user, elem))

                    g.db.add(user)
                    user.email_confirmed = True
                    g.db.commit()

                if user.banned:
                    flash('Sorry, you cannot login into the Profireader. Contact the profireader'
                          'administrator, please: ' + current_app.config['PROFIREADER_MAIL_SENDER'])

                    return redirect(url_for('index.index'))

                # session['user_id'] = user.id assignment
                # is automatically executed by login_user(user)
                if user:
                    login_user(user)
                    flash("You were successfully logged in")
                    if portal_id:
                        session.pop('portal_id')
                        return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
                    elif back_to:
                        session.pop('back_to')
                        return redirect(back_to)
                    # return redirect(request.args.get('next') or url_for('index.index'))
                    return redirect(redirect_url())
                # return redirect(url_for('index.index'))  # #  http://profireader.com/
                # url = redirect_url()
                # print(url)
                if registred_via_soc:
                    return redirect(url_for('help.help'))

                return redirect(redirect_url())  # #  http://profireader.com/
            elif result.error:
                redirect_path = '#/?msg={}'.format(quote(soc_network_names[-1] + ' login failed.'))
                return redirect(redirect_path)
    except:
        print(sys.exc_info()[0])
        raise
    return response


# @auth_bp.before_app_request
# def before_request():
#     if current_user.is_authenticated():
#         current_user.ping()
#         if not current_user.email_confirmed and request.endpoint[:5] != 'auth.' and request.endpoint != 'static' and \
#                 not (request.endpoint == 'tools.save_translate' or request.endpoint == 'tools.change_allowed_html' or request.endpoint == 'tools.update_last_accessed'):
#             return redirect(url_for('auth.unconfirmed'))


@auth_bp.route('/login_signup/', methods=['GET'])
@check_right(AllowAll)
def login_signup_endpoint():
    if current_user.is_authenticated():
        if session.get('portal_id'):
            return redirect(url_for('index.reader_subscribe', portal_id=session['portal_id']))
        elif session.get('back_to'):
            return redirect(session['back_to'])

    login_signup = request.args.get('login_signup', 'login')
    return render_template('auth/login_signup.html',
                           login_signup=login_signup)


@auth_bp.route('/login_signup/', methods=['OK'])
@check_right(AllowAll)
def signup(json_data):
    action = g.req('action', allowed=['validate', 'save'])

    params = g.filter_json(json_data, 'first_name,last_name,email,password,password_confirmation')
    params['address_email'] = params['email']
    del params['email']
    new_user = User(**params)

    if action == 'validate':
        return new_user.validate(True)
    else:
        try:
            if session.get('portal_id'):
                addtourl = {'subscribe_to_portal': session['portal_id']}
                session.pop('portal_id')
            else:
                addtourl = {}
            new_user.set_password_hash()
            new_user.generate_confirmation_token(addtourl).save()
            g.db.commit()
            return {}
        except:
            return {'error': 'signup error'}


@auth_bp.route('/login/', methods=['OK'])
@check_right(AllowAll)
def login(json_data):
    # portal = Portal.get(session.get('portal_id'), True)
    # # back_to = session.get('back_to')
    # if current_user.is_authenticated() and portal:
    #     session.pop('portal_id')
    #     current_user.subscribe_user()
    #     return redirect(url_for('index.index'))
    email = json_data.get('email', '')
    password = json_data.get('password', '')

    user = g.db.query(User).filter(User.address_email == email).first()

    if user and user.banned:
        flash()
        return {'error': 'You can not be logged in. Please contact the Profireader administration'}
    elif user and not user.email_confirmed:
        return {'error': 'You email is unconfirmed. Please confirm your email'}
    elif not user or not user.verify_password(password):
        return {'error': 'Email or password is wrong'}
    else:
        user.login()
        return {}
        # if portal_id:
        #     session.pop('portal_id')
        #     return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
        # elif back_to:
        #     session.pop('back_to')
        #     return redirect(back_to)
        # # return redirect(request.args.get('next') or url_for('index.index'))
        # return redirect(redirect_url())
        # flash('Invalid username or password.')
        # redirect_url_str = url_for('auth.login_signup_endpoint') + '?login_signup=login'
        # redirect_url += ('&' + 'portal_id=' + portal_id) if portal_id else ''
        # return redirect(redirect_url_str)


@auth_bp.route('/email_confirmation/', methods=['GET'])
@auth_bp.route('/email_confirmation/<string:token>/', methods=['GET'])
@check_right(AllowAll)
def email_confirmation(token=None):
    email = request.args.get('email', None)

    if not token:
        return render_template("auth/email_confirmation_enter_token.html", email='')

    user = db(User, email_conf_token=token).first()

    if not user:
        return render_template("auth/email_confirmation_enter_token.html", email='', wrong_token_entered=True)
    elif not user.confirm_email():
        return render_template("auth/email_confirmation_enter_token.html", email=user.address_email,
                               wrong_token_entered=True)
    elif user.email_confirmed:
        return render_template("auth/email_confirmation_enter_token.html", email=email, already_confirmed=True)
    else:
        User.logout()
        user.save()
        g.db.commit()
        user.login()
        portal = Portal.get(request.args.get('subscribe_to_portal'), returnNoneIfNotExists=True)
        if portal:
            portal.subscribe_user(user)
        return redirect(url_for('auth.welcome'))

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
                user.generate_confirmation_token({}).save()
                return {}
        else:
            return {'error': 'User with this email is not registered'}



            # @auth_bp.route('/tos/', methods=['GET'])
# @check_right(AllowAll)
# def tos():
#     if not g.user or g.user.tos:
#         return redirect(url_for('index.welcome'))
#     else:
#         return render_template("auth/tos.html")
#
#
@auth_bp.route('tos/', methods=['OK'])
@check_right(AllowAll)
def tos(json):
    if json.get('accept', False):
        current_user.tos = True
        current_user.save()
        return current_user.tos
    else:
        return {'error': 'tos acceptation error'}


        # user = db(User, email_conf_token=token).first()
        # portal_id = request.args.get('subscribe_to_portal')
        # if user and user.email_confirmed:
        #     return render_template("auth/confirm_email.html", message='Your account has been already confirmed!')
        # elif not user or not user.confirm_email():
        #     return render_template("auth/unconfirmed.html", message='Wrong or expired token',
        #                            email=user.address_email if user else '')
        # else:
        #     logout_user()
        #     user.email_confirmed = True
        #     user.save()
        #     login_user(user)
        #     if portal_id:
        #         return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
        #     return render_template("auth/confirm_email.html")


# @auth_bp.route('/signup/', methods=['POST'])
# @check_right(AllowAll)
# def signup():
#     # if g.user_init and g.user_init.is_authenticated():
#
#     email = request.form.get('email')
#     display_name = request.form.get('display_name')
#     password = request.form.get('password')
#
#     def check_fields():
#         form = request.form
#         required_fields = ['email', 'display_name', 'password', 'password1']
#         for field in required_fields:
#             if field not in form.keys():
#                 return False
#             else:
#                 if not form.get(field):
#                     return False
#                 elif form.get('password') != form.get('password1'):
#                     return False
#         if db(User, address_email=request.form.get('email')).first():
#             flash('User with this email already exist')
#             return False
#         return True
#
#     if check_fields():  # # pass1 == pass2
#         profireader_all = SOC_NET_NONE['profireader'].copy()
#         profireader_all['email'] = email
#         profireader_all['name'] = display_name
#         user = User(
#             PROFIREADER_ALL=profireader_all,
#             password=password  # # pass is automatically hashed
#         )
#         user.generate_confirmation_token()
#         g.db.add(user)
#         g.db.commit()
#         addtourl = {}
#         if session.get('portal_id'):
#             addtourl['subscribe_to_portal'] = session['portal_id']
#             session.pop('portal_id')
#         SendEmail().send_email(subject='Confirm Your Account',
#                                html=render_template('auth/email/resend_confirmation.html', user=user,
#                                                     addtourl=addtourl),
#                                send_to=(user.address_email,))
#         flash('A confirmation email has been sent to you by email.')
#         return redirect(url_for('auth.login_signup_endpoint'))
#     return render_template('auth/login_signup.html',
#                            login_signup='signup')


# TODO: YG by OZ:
@auth_bp.route('//', methods=['POST'])
@auth_bp.route('/login_signup/<soc_network_name>', methods=['GET', 'POST'])
@check_right(AllowAll)
def login_signup_soc_network(soc_network_name):
    ret = login_signup_general('profireader', soc_network_name)
    return ret


# @auth_bp.route('/login/<soc_network_name>', methods=['GET', 'POST'])
# def login_soc_network(soc_network_name):
# return login_signup_general(soc_network_name)
# return login_signup_general('profireader', soc_network_name)


# @auth_bp.route('/signup/<soc_network_name>', methods=['GET', 'POST'])
# def login_signup_soc_network(soc_network_name):
#     return redirect(url_for('auth.login_soc_network', soc_network_name=soc_network_name))
# return login_signup_general('profireader', soc_network_name)


# read: flask.ext.login
# On a production server, the login route must be made available over
# secure HTTP so that the form data transmitted to the server is en‐
# crypted. Without secure HTTP, the login credentials can be intercep‐
# ted during transit, defeating any efforts put into securing passwords
# in the server.
#
# read this!: http://flask.pocoo.org/snippets/62/
# @auth_bp.route('/login/', methods=['POST'])
# @check_right(AllowAll)
# def login():
#     # if g.user_init and g.user_init.is_authenticated():
#     # portal_id = request.args.get('subscribe', None)
#
#     portal_id = session.get('portal_id')
#     back_to = session.get('back_to')
#     if current_user.is_authenticated():
#         if portal_id:
#             session.pop('portal_id')
#             return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
#         flash('You are already logged in. If you want to login with another account logout first please')
#         return redirect(url_for('index.index'))
#     email = request.form.get('email')
#     password = request.form.get('password')
#
#     if email and password:
#
#         user = g.db.query(User).filter(User.address_email == email).first()
#
#         if user and user.banned:
#             flash('You can not be logged in. Please contact the Profireader administration.')
#             return redirect(url_for('index.index'))
#         if user and user.verify_password(password):
#
#             login_user(user)
#             flash("You were successfully logged in")
#             if portal_id:
#                 session.pop('portal_id')
#                 return redirect(url_for('index.reader_subscribe', portal_id=portal_id))
#             elif back_to:
#                 session.pop('back_to')
#                 return redirect(back_to)
#             # return redirect(request.args.get('next') or url_for('index.index'))
#             return redirect(redirect_url())
#         flash('Invalid username or password.')
#         redirect_url_str = url_for('auth.login_signup_endpoint') + '?login_signup=login'
#         # redirect_url += ('&' + 'portal_id=' + portal_id) if portal_id else ''
#         return redirect(redirect_url_str)
#     return render_template('auth/login_signup.html',
#                            login_signup='login')


@auth_bp.route('/logout/', methods=['GET'])
@login_required
@check_right(AllowAll)
def logout():
    User.logout()
    return redirect(url_for('index.index'))


# @auth_bp.route('/unconfirmed', methods=['GET'])
# @check_right(AllowAll)
# def unconfirmed():
#     if current_user.email_confirmed:
#         return redirect(url_for('index.index'))
#     return render_template('auth/unconfirmed.html')


# @auth_bp.route('/tos', methods=['OK'])
# @login_required
# @check_right(AllowAll)
# def tos(json):
#     g.user.tos = json['accept'] == 'accept'
#     return {'tos': g.user.tos}



# @auth_bp.route('/change-password', methods=['GET', 'OK'])
# @login_required
# def change_password():
#     form = ChangePasswordForm()
#     if form.validate_on_submit():
#         if current_user.verify_password(form.old_password.data):
#             current_user.password = form.password.data
#             g.db.add(current_user)
#             g.db.commit()
#             flash('Your password has been updated.')
#             return redirect(url_for('index.index'))
#         else:
#             flash('Invalid password.')
#     return render_template("auth/bak_change_password.html", form=form)

@auth_bp.route('/reset_password', methods=['GET'])
@check_right(AllowAll)
def reset_password():
    return render_template('auth/reset_password.html')


@auth_bp.route('/reset_password', methods=['OK'])
@check_right(AllowAll)
def reset_password_request(json):
    if not current_user.is_anonymous():
        flash('To reset your password logout first please.')
        redirect(url_for('index.list_reader'))
        return False

    user = db(User, address_email=json.get('email')).first()
    if user:
        user.generate_pass_reset_token().save()
        SendEmail().send_email(subject='Reset password', send_to=(user.address_email, ""),
                               html=render_template('auth/email/reset_password.html', user=user), )
        flash('An email with instructions to reset your password has been sent to you.')
    else:
        flash('You are not Profireader user yet. Sign up Profireader first please.')
    return {}


@auth_bp.route('/reset/<token>', methods=['GET'])
@check_right(AllowAll)
def password_reset(token):
    if not current_user.is_anonymous():
        return redirect(url_for('auth/reset_password_token.html'))
    return render_template('auth/reset_password_token.html', token=token)


@auth_bp.route('/reset/<token>', methods=['OK'])
@check_right(AllowAll)
def password_reset_change(json, token):
    user = g.db.query(User). \
        filter_by(address_email=json['data'].get('email')).first()
    if not user or user.pass_reset_token != token:
        return 'Your put wrong email.'

    def check_fields():
        required_fields = ['email', 'password', 'password1']
        for field in required_fields:
            if field not in json['data'].keys():
                return 'Data is wrong.'
            else:
                if not json['data'].get(field):
                    return 'Fill all fields.'
                elif json['data'].get('password') != json['data'].get('password1'):
                    return 'Put the same passwords.'
        return True

    check = check_fields()
    if check == True:
        if (user is None) or user.banned:
            return 'You cannot update password.You are baned.'
        if user.reset_password(json['data'].get('password')):
            return True
        else:
            return 'Something wrong.'
    else:
        return check

# наразі не використовується але потрібна в майбутньому
# @auth_bp.route('/change-email', methods=['GET', 'POST'])
# @login_required
# def change_email_request():
#     form = ChangeEmailForm()
#     if form.validate_on_submit():
#         if current_user.verify_password(form.password.data):
#             new_email = form.email.data
#             token = current_user.generate_email_change_token(new_email)
#             SendEmail().send_email(subject='Confirm your email address', template='auth/email/change_email',
#                                    send_to=(new_email, ), user=current_user, token=token)
#             flash('An email with instructions to confirm your new email address has been sent to you.')
#             return redirect(url_for('index.index'))
#         else:
#             flash('Invalid email or password.')
#     return render_template("auth/change_email.html", form=form)
#
#
# @auth_bp.route('/change-email/<token>')
# @login_required
# def change_email(token):
#     if current_user.change_email(token):
#         flash('Your email address has been updated.')
#         g.db.add(current_user)
#         g.db.commit()
#     else:
#         flash('Invalid request.')
#     return redirect(url_for('index.index'))
