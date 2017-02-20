from flask import render_template, abort, g
from flask import session

from config import Config

from .blueprints_declaration import user_bp
from .. import utils
from ..constants.UNCATEGORIZED import AVATAR_SIZE
from ..models.dictionary import Country
from ..models.permissions import UserIsActive, UserIsAdmin, UserIsOwner
from ..models.users import User


@user_bp.route('/<user_id>/profile/', permissions=UserIsActive())
def profile(user_id):
    user = g.db.query(User).filter(User.id == user_id).first()
    if not user:
        abort(404)
    return render_template('general/user_profile.html', user=user, avatar_size=AVATAR_SIZE,
                           actions={'edit_user_profile':
                                        (UserIsOwner() | UserIsAdmin()).check(user_id = user_id)})


@user_bp.route('/<user_id>/edit-profile/', methods=['GET'], permissions=UserIsOwner() | UserIsAdmin())
def edit_profile(user_id):
    user_query = utils.db.query_filter(User, id=user_id)
    user = user_query.first()
    return render_template('general/user_edit_profile.html', user=user)


@user_bp.route('/<user_id>/edit-profile/', methods=['OK'], permissions=UserIsOwner() | UserIsAdmin())
def edit_profile_load(json, user_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])
    user = User.get(user_id)
    if action == 'load':
        ret = {'user': user.get_client_side_dict(), 'languages': Config.LANGUAGES,
               'countries': Country.get_countries()}
        ret['user']['avatar'] = user.avatar
        return ret
    else:
        user_data = utils.filter_json(json['user'],
                                      'first_name, last_name, birth_tm, lang, country_id, location, gender, address_url, address_phone, address_city, address_location, about, password, password_confirmation')

        user_data['country_id'] = user_data['country_id'] if user_data[
            'country_id'] else '56f52e6b-1273-4001-b15d-d5471ebfc075'
        user_data['full_name'] = user_data['first_name'] + ' ' + user_data['last_name']
        user_data['birth_tm'] = user_data['birth_tm'] if user_data['birth_tm'] else None
        avatar = json['user']['avatar']
        user.attr(user_data)
        if user.password == '':
            user.password = None
        if action == 'validate':
            user.detach()
            validate = user.validate(False)
            return validate
        else:
            user.avatar = avatar
            user.set_password_hash()
            ret = {'user': user.save().get_client_side_dict()}
            return ret


@user_bp.route('/change_lang/', methods=['OK'], permissions=UserIsActive())
def change_language(json):
    if g.user:
        g.user.lang = json.get('language')
        g.user.save()

    session['language'] = json.get('language')
    g.lang = json.get('language')
