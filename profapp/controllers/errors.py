from flask import render_template
from flask_wtf.csrf import CsrfProtect
from .blueprints import error_bp

csrf = CsrfProtect()


class Error(Exception):
    pass


class BadCoordinates(Error):
    pass


class BadFormatFile(Error):
    pass


class EmptyFieldName(Error):
    pass


class UserNotFoundError(Error):
    pass


class BadDataProvided(Error):
    pass


class DublicateName(Error):
    pass


@csrf.error_handler
def csrf_error(reason):
    return render_template('404.html',
                           reason=reason), 400


@error_bp.errorhandler(404)
def page_not_found(reason):
    return render_template('404.html',
                           reason=reason), 404
