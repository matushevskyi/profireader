from .blueprints import user_bp
from flask import url_for, render_template, abort, request, flash, redirect
from db_init import db_session
from ..models.users import User
from flask.ext.login import current_user, login_required
#from ..constants.PROFILE_NECESSARY_FIELDS import PROFILE_NECESSARY_FIELDS
from ..forms.user import EditProfileForm
from flask import g



#@user_bp.route('/profile/<user_id>', methods=['GET', 'POST'])
#def profile_old(user_id):
#    user_subject = db_session.query(User).filter(User.id == user_id).first()
#    name = user_subject.user_name()
#    user = {'id': user_id, 'name': name}
#    return render_template(url_for('general.index', user=user))


@user_bp.route('/profile/<user_id>')
@login_required
def profile(user_id):
    user = db_session.query(User).\
        filter(User.id == user_id).first()
    if not user:
        abort(404)
    return render_template('user_profile.html')


@user_bp.route('/edit-profile/<user_id>', methods=['GET', 'POST'])
@login_required
def edit_profile(user_id):
    user = db_session.query(User).\
        filter(User.id == user_id).first()
    if not user:
        abort(404)
    if current_user != user:
        abort(403)
    #form = EditProfileForm()
    #if form.validate_on_submit():
    #    pass
    #pass

    if request.method == 'GET':
        return render_template('user_edit_profile.html')

    user.profireader_name = request.form['name']
    user.profireader_first_name = request.form['first_name']
    user.profireader_last_name = request.form['last_name']
    user.profireader_gender = request.form['gender']
    user.profireader_link = request.form['link']
    user.profireader_phone = request.form['phone']
    user.location = request.form['location']
    user.about_me = request.form['about_me']
    db_session.add(user)
    db_session.commit()
    flash('You have successfully updated you profile.')

    return redirect(url_for('user.profile', user_id=user_id))
