from .blueprints_declaration import messenger_bp
from flask import render_template


@messenger_bp.route('/')
def messenger():
    return render_template('messenger/messenger.html')
