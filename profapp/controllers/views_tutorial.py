from .blueprints_declaration import tutorial_bp
from flask import render_template
from ..models.permissions import AvailableForAll

@tutorial_bp.route('/', permissions=AvailableForAll())
def index():
    return render_template('/tutorial.html')
