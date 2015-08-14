from .blueprints import user_bp
from flask import jsonify, make_response, g, session, request, redirect, \
    url_for, render_template, flash
from authomatic.adapters import WerkzeugAdapter
from ..models.users import User
from db_init import db_session
from ..constants.USER_REGISTERED import REGISTERED_WITH_FLIPPED
from ..constants.SOCIAL_NETWORKS import DB_FIELDS, SOC_NET_FIELDS
from flask.ext.login import login_user, logout_user, current_user, \
    login_required
import sqlalchemy.exc as sqlalchemy_exc

from urllib.parse import quote
from ..models.users import User
#from ..utils import login_required
import json

#def _session_saver():
#    session.modified = True

import re
from authomatic.adapters import WerkzeugAdapter

from flask import redirect, make_response
from flask.ext.login import login_user
from ..constants.SOCIAL_NETWORKS import SOC_NET_NONE


EMAIL_REGEX = re.compile(r'[^@]+@[^@]+\.[^@]+')


#provider_name:
# 0) profireader+
# 1) facebook +-
# 2) linkedin +
# 3) google +
# 4) twitter +
# 5) microsoft +
# 6) yahoo +


@user_bp.route('/signup/', methods=['GET', 'POST'])
def signup():
    if g.user_init and g.user_init.is_authenticated():
        if request.url:
            return redirect(request.url)
        return redirect(url_for('general.index'))

    if request.method == 'GET':
        return render_template('signup.html', user=g.user_dict)
    else:
        user_name = request.form['display-name']
        user_email = request.form['email']
        user_password = request.form['password']
        user_password2 = request.form['password2']
        if user_password != user_password2:
            flash('your password confirmation doesnt match the password',
                  'error')
            return redirect(url_for('user.signup'))
        user = db_session.query(User).\
                    filter(User.profireader_email == user_email).first()
        if user:
            flash('such user is already registered')
            return redirect(url_for('user.signup'))

        profireader_all = SOC_NET_NONE['PROFIREADER']
        profireader_all['EMAIL'] = user_email
        profireader_all['NAME'] = user_name
        user = User(
            PROFIREADER_ALL=profireader_all,
        )
        user.password = user_password  # pass here is authomatically hashed
        db_session.add(user)
        db_session.commit()
        session['user_id'] = user.id

        return redirect('/')  # #  http://aprofi.d.ntaxa.com/



@user_bp.route('/profile/<user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user_subject = db_session.query(User).filter(User.id == user_id).first()
    name = user_subject.user_name()
    user = {'id': user_id, 'name': name}
    return render_template('index.html', user=user)

# @user_bp.route('/delete/<int:x>', methods=['GET', 'POST'])
# def delete(x):
#     return render_template('profile.html', x=x)


# read: flask.ext.login
# TODO: make a logic when login is possible only if user is NOT logged
# On a production server, the login route must be made available over
# secure HTTP so that the form data transmitted to the server is en‐
# crypted. Without secure HTTP, the login credentials can be intercep‐
# ted during transit, defeating any efforts put into securing passwords
# in the server.
#
# read this before push!!!: http://flask.pocoo.org/snippets/62/
@user_bp.route('/login/', methods=['GET'])
def login():
    return render_template('login.html', user=g.user_dict)


@user_bp.route('/signup/profireader/validate/', methods=['POST'])
def signup_profireader_validate():
    user = User(PROFIREADER_ALL={'email': '11', 'password': '22'})
    a = 1
    return jsonify({'ok': False, 'errors': {'email': 'wrong email'}})


@user_bp.route('/login/profireader/', methods=['POST'])
def login_profireader():
    if g.user_init and g.user_init.is_authenticated():
        if request.url:
            return redirect(request.url)
        return redirect(url_for('general.index'))

    if request.method == 'GET':
        return render_template('login.html', user=g.user_dict)
    else:
        # add code here to validate input data
        user_email = request.form['email']
        user_password = request.form['password']

        user = db_session.query(User).\
            filter(User.profireader_email == user_email).first()

        if user:
            if user.verify_password(user_password):
                session['user_id'] = user.id

                #  the code below should be tuned.
                return redirect(request.args.get('next') or
                                url_for('general.index'))

        flash('Invalid username or password.')
        return redirect(url_for('user.login'))


# TODO: just complete this
# TODO: if registration was via email
# TODO: we should make validation!

# TODO: consider the situation when
# TODO: we have really profile_completed = True
# TODO: it is only possible when user was registered
# TODO: via email
# email_conf_key=None, email_conf_tm=None, pass_reset_key=None,
# pass_reset_conf_tm=None, registered_via=None, ):
# important: http://flask.pocoo.org/snippets/62/
#@user_bp.route('/login/profireader', methods=['GET', 'POST'])
#def login_profireader():
#    email = .....email
#    if email and EMAIL_REGEX.match(email):
#          user = User.query.filter_by(email=email).first()
#          if user:
#              login_user(user)
#              return redirect(url_for('general.index'))
#    #      return redirect(url_for('general.index'))  #  delete this redirect
#    user.pass_salt_generation
#    return render_template(url_for('general.index'))


# it is valid only if registration was via soc network
@user_bp.route('/login/<soc_network_name>', methods=['GET', 'POST'])
def login_soc_network(soc_network_name):
    response = make_response()
    try:
        result = g.authomatic.login(WerkzeugAdapter(request, response),
                                    soc_network_name)
        if result:
            if result.user:
                result.user.update()
                result_user = result.user
                db_fields = DB_FIELDS[soc_network_name.upper()]
                user = db_session.query(User).\
                    filter(getattr(User, db_fields['ID']) == result_user.id)\
                    .first()
                if not user:
                    user = User()
                    for elem in SOC_NET_FIELDS:
                        setattr(user, db_fields[elem],
                                getattr(result_user, elem.lower()))
                    db_session.add(user)
                    db_session.commit()
                session['user_id'] = user.id

                return redirect('/')  # #  http://aprofi.d.ntaxa.com/
            elif result.error:
                redirect_path = '#/?msg={}'.\
                    format(quote(soc_network_name + ' login failed.'))
                return redirect(redirect_path)

    except:
        import sys
        print(sys.exc_info())
        raise
    return response


#@user_bp.route('/login/fb/', methods=['GET', 'POST'])
#def login_fb():
#    response = make_response()
#    result = g.authomatic.login(WerkzeugAdapter(request, response), 'fb',
#                                session=session,
#                                session_saver=_session_saver)
#    if result:
#        if result.user:
#            result.user.update()
#            user = User.query.filter_by(fb_id=result.user.id).first()
#            if not user:
#                user = User(result.user.first_name,
#                            result.user.last_name,
#                            result.user.id,
#                            result.user.email)
#                #db.session.add(user)
#                #db.session.commit()
#            session['user_id'] = user.id
#            return redirect('/')
#
#        elif result.error:
#            redirect_path = '#/?msg={}'.format(quote('Facebook login failed.'))
#            return redirect(redirect_path)
#    return response


#
#
#@user_bp.route('/user-info/', methods=['GET'])  # user profile
#def user_info():
#    res = {}
#    if g.user:
#        res = (
#            {'id': g.user.id, 'first_name': g.user.fb_first_name,
#             'last_name': g.user.fb_last_name,
#             'fb_id': g.user.fb_id,
#             'email': g.user.email})
#    return jsonify(res)
#


@user_bp.route('/logout/', methods=['GET'])
@login_required   # Only logged in user can be logged out
def logout():
    # session.pop('user_id', None)

    # from flask.ext.login import logout_user, login_required
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('general.index'))
