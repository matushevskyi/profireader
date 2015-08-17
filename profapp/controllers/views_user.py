from .blueprints import user_bp
from flask import url_for, render_template
from db_init import db_session
from ..models.users import User


@user_bp.route('/profile/<user_id>', methods=['GET', 'POST'])
def profile(user_id):
    user_subject = db_session.query(User).filter(User.id == user_id).first()
    name = user_subject.user_name()
    user = {'id': user_id, 'name': name}
    return render_template(url_for('general.index', user=user))

# @user_bp.route('/delete/<int:x>', methods=['GET', 'POST'])
# def delete(x):
#     return render_template('profile.html', x=x)
