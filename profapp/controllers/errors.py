from flask import render_template, flash
from flask_wtf.csrf import CsrfProtect
from .blueprints_declaration import exception_bp

csrf = CsrfProtect()


class Error(Exception):
    pass


class RightsTypeIntError(Error):
    pass


class RightsTypeIterableError(Error):
    pass


class RightsDefUndefInconsistencyError(Error):
    pass


class ImproperRightsDecoratorUse(Error):
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


class StatusNonActivate(Error):
    pass


class SubscribeToOwn(Error):
    pass


class PortalAlreadyExist(Error):
    # except errors.PortalAlreadyExist as e:
    #     details = e.args[0]
    #     print(details['message'])
    pass


class AlreadyJoined(Error):
    pass


class BadTypeProvided(Error):
    pass


class TooManyCredentialsInDb(Error):
    pass


class VideoAlreadyExistInPlaylist(Error):
    pass


class ValidationException(Error):
    """ Inappropriate argument value (of correct type). """

    def __init__(self, validation_result):  # real signature unknown
        self.result = validation_result
        pass


class WrongNumberOfParameters(Error):
    pass


class WrongMandatoryParametersPassedToFunction(Error):
    pass


class NoRights(Exception):
    url = '/'

    def __init__(self, redirect_to='/'):
        self.url = redirect_to

#
# @csrf.error_handler
# def csrf_error(reason):
#     return render_template('errors/404.html', reason=reason), 400
#
#
# @exception_bp.errorhandler(404)
# def page_not_found(reason):
#     return render_template('errors/404.html', reason=reason), 404
