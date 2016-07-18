from .blueprints_declaration import user_bp
from flask import url_for, render_template, abort, request, flash, redirect, \
    request, g
from ..models.users import User
from utils.db_utils import db
from ..constants.UNCATEGORIZED import AVATAR_SIZE
from ..controllers.request_wrapers import check_right
from config import Config
from ..models.country import Country
from flask import session
from ..models.rights import UserIsActive, UserEditProfieRight, AllowAll
from .. import utils


@user_bp.route('/profile/<user_id>')
@check_right(UserIsActive)
def profile(user_id):
    user = g.db.query(User).filter(User.id == user_id).first()
    if not user:
        abort(404)
    return render_template('general/user_profile.html', user=user, avatar_size=AVATAR_SIZE,
                           actions={'edit_user_profile': UserEditProfieRight(user=user).is_allowed() == True})


# TODO (AA to AA): Here admin must have the possibility to change user profile
@user_bp.route('/edit-profile/<user_id>/', methods=['GET'])
@check_right(UserEditProfieRight, ['user_id'])
def edit_profile(user_id):
    user_query = db(User, id=user_id)
    user = user_query.first()
    return render_template('general/user_edit_profile.html', user=user)


@user_bp.route('/edit-profile/<user_id>/', methods=['OK'])
@check_right(UserEditProfieRight, ['user_id'])
def edit_profile_load(json, user_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    if action == 'load':
        ret = {'user': g.user.get_client_side_dict(), 'languages': Config.LANGUAGES,
               'countries': Country.get_countries(), 'change_password': {'password1': '', 'password2': ''}}
        ret['user']['avatar'] = g.user.avatar
        return ret
    else:
        user_data = utils.filter_json(json['user'],
                                      'first_name, last_name, birth_tm, lang, country_id, location, gender, address_url, address_phone')

        user_data['country_id'] = user_data['country_id'] if user_data[
            'country_id'] else '56f52e6b-1273-4001-b15d-d5471ebfc075'
        user_data['full_name'] = user_data['first_name'] + ' ' + user_data['last_name']
        user_data['birth_tm'] = user_data['birth_tm'] if user_data['birth_tm'] else None
        avatar = json['user']['avatar']
        g.user.attr(user_data)
        if action == 'validate':
            g.user.detach()
            validate = g.user.validate(False)
            if json['change_password']['password1'] != json['change_password']['password2']:
                validate['errors']['password2'] = 'pls enter the same passwords'
            return validate
        else:
            if json['change_password']['password1']:
                g.user.password = json['change_password']['password1']
            g.user.avatar = avatar
            ret = {'user': g.user.save().get_client_side_dict()}

            return ret


@user_bp.route('/change_lang/', methods=['OK'])
@check_right(AllowAll)
def change_language(json):
    if g.user:
        g.user.lang = json.get('language')
        g.user.save()
    else:
        session['language'] = json.get('language')
        g.lang = json.get('language')
