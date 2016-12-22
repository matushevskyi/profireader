from flask import url_for, session
from config import Config


def back_to_url(endpoint, host=Config.MAIN_DOMAIN, **endpoint_params):
    back_to = '//{host}{endpoint}'.format(host=host, endpoint=url_for(endpoint, **endpoint_params))
    session['back_to'] = back_to
    return back_to
