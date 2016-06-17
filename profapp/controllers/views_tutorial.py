from .blueprints_declaration import tutorial_bp
from flask import render_template


@tutorial_bp.route('/')
def tutorial():
    return render_template('tutorial.html')
