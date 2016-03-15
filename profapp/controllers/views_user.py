from .blueprints_declaration import user_bp
from flask import url_for, render_template, abort, request, flash, redirect, \
    request, g
# from db_init import db_session
from ..models.users import User
from flask.ext.login import current_user, login_required
from utils.db_utils import db
from ..constants.UNCATEGORIZED import AVATAR_SIZE, AVATAR_SMALL_SIZE
from ..forms.user import EditProfileForm
from ..controllers.request_wrapers import tos_required
from .request_wrapers import ok
from config import Config
from ..models.country import Country


@user_bp.route('/profile/<user_id>')
@tos_required
@login_required
def profile(user_id):
    user = g.db.query(User).filter(User.id == user_id).first()
    if not user:
        abort(404)
    return render_template('general/user_profile.html', user=user, avatar_size=AVATAR_SIZE)


@user_bp.route('/avatar_update')
@ok
def avatar_update(json):
    image = json.get('update_image')
    user = json.get('user')
    return user.avatar_update(image)


# TODO (AA to AA): Here admin must have the possibility to change user profile
@user_bp.route('/edit-profile/<user_id>/', methods=['GET'])
@tos_required
@login_required
def edit_profile(user_id):
    if current_user.get_id() != user_id:
        abort(403)
    user_query = db(User, id=user_id)
    user = user_query.first()
    return render_template('general/user_edit_profile.html', user=user)


@user_bp.route('/edit-profile/<user_id>/', methods=['POST'])
@tos_required
@login_required
@ok
def edit_profile_load(json, user_id):
    action = g.req('action', allowed=['load', 'validate', 'save'])

    # user_query = db(User, id=user_id)


    # user = user_query.first()

    if action == 'load':
        ret = {'user': g.user.get_client_side_dict(), 'languages': Config.LANGUAGES,
               'countries': Country.get_countries(), 'avatar': {}}
        ret['avatar'] = g.user.get_image_client_dict()
        return ret
    else:
        g.user.updates(json['user'])
        if action == 'validate':
            g.user.detach()
            return g.user.validate(False)
        else:
            g.user.save()
            return {'user': g.user.get_client_side_dict()}

    return {user: user}
