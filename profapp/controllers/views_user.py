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
        ret['user']['avatar'] = g.user.get_avatar_client_side_dict()
        return ret
    else:
        json['user']['profireader_name'] = json['user']['profireader_first_name']+' '+json['user']['profireader_last_name']
        g.user.attr(json['user'])
        if action == 'validate':
            g.user.detach()
            validate = g.user.validate(False)
            if json['change_password']['password1'] != json['change_password']['password2']:
                validate['errors']['password2'] = 'pls enter the same passwords'
            return validate
        else:
            if json['change_password']['password1']:
                g.user.password = json['change_password']['password1']
            g.user.set_avatar_client_side_dict(json['user']['avatar']).save()
            ret = {'user': g.user.get_client_side_dict()}
            ret['user']['avatar'] = g.user.get_avatar_client_side_dict()
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
