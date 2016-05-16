from .blueprints_declaration import messenger_bp
from flask import render_template
from .request_wrapers import check_right
from ..models.rights import AllowAll

@messenger_bp.route('/')
@check_right(AllowAll)
def messenger():
    return render_template('messenger/messenger.html')
