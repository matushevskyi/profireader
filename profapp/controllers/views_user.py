from flask import render_template, abort, g
from flask import session

from config import Config

from .blueprints_declaration import user_bp
from .. import utils
from ..constants.UNCATEGORIZED import AVATAR_SIZE
from ..controllers.request_wrapers import check_right
from ..models.dictionary import Country
from ..models.rights import UserIsActive, UserEditProfieRight, AllowAll
from ..models.users import User


@user_bp.route('/<user_id>/profile/')
@check_right(UserIsActive)
def profile(user_id):
    user = g.db.query(User).filter(User.id == user_id).first()
    if not user:
        abort(404)
    return render_template('general/user_profile.html', user=user, avatar_size=AVATAR_SIZE,
                           actions={'edit_user_profile': UserEditProfieRight(user=user).is_allowed() == True})


# TODO (AA to AA): Here admin must have the possibility to change user profile
@user_bp.route('/<user_id>/edit-profile/', methods=['GET'])
@check_right(UserEditProfieRight, ['user_id'])
def edit_profile(user_id):
    user_query = utils.db.query_filter(User, id=user_id)
    user = user_query.first()
    return render_template('general/user_edit_profile.html', user=user)


@user_bp.route('/<user_id>/edit-profile/', methods=['OK'])
@check_right(UserEditProfieRight, ['user_id'])
def edit_profile_load(json, user_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    if action == 'load':
        ret = {'user': g.user.get_client_side_dict(), 'languages': Config.LANGUAGES,
               'countries': Country.get_countries()}
        ret['user']['avatar'] = g.user.avatar
        return ret
    else:
        user_data = utils.filter_json(json['user'],
                                      'first_name, last_name, birth_tm, lang, country_id, location, gender, address_url, address_phone, address_city, address_location, about, password, password_confirmation')

        user_data['country_id'] = user_data['country_id'] if user_data[
            'country_id'] else '56f52e6b-1273-4001-b15d-d5471ebfc075'
        user_data['full_name'] = user_data['first_name'] + ' ' + user_data['last_name']
        user_data['birth_tm'] = user_data['birth_tm'] if user_data['birth_tm'] else None
        avatar = json['user']['avatar']
        g.user.attr(user_data)
        if g.user.password == '':
            g.user.password = None
        if action == 'validate':
            g.user.detach()
            validate = g.user.validate(False)
            return validate
        else:
            g.user.avatar = avatar
            g.user.set_password_hash()
            ret = {'user': g.user.save().get_client_side_dict()}
            return ret


@user_bp.route('/change_lang/', methods=['OK'])
@check_right(AllowAll)
def change_language(json):
    if g.user:
        g.user.lang = json.get('language')
        g.user.save()

    session['language'] = json.get('language')
    g.lang = json.get('language')
