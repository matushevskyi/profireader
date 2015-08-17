from flask import render_template, g
from . import blueprints
from ..models.user_model import User

@blueprints.general_bp.route('')
def index():
    return render_template('index.html', user=g.user_dict)
