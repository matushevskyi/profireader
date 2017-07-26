from flask import url_for


class PRException(Exception):
    redirect_to = None

    def __init__(self, message='Unknown exception', redirect_to=None):
        self.redirect_to = redirect_to
        super(PRException, self).__init__(message)


class NotLoggedInUser(PRException):
    def __init__(self, message='User is not logged in. Please log in', redirect_to=None):
        super(NotLoggedInUser, self).__init__(message, redirect_to=redirect_to if redirect_to else
        url_for('auth.login_signup_endpoint'))


class BannedUser(PRException):
    def __init__(self, message='User is baned. pls contact administrator'):
        super(BannedUser, self).__init__(message)


class UnauthorizedUser(PRException):
    def __init__(self, message='User is unauthorized to do this. go away', redirect_to='/'):
        super(UnauthorizedUser, self).__init__(message, redirect_to=redirect_to)


class UnconfirmedEmailUser(PRException):
    def __init__(self, message='Email is unconfirmed. pls confirm email'):
        super(UnconfirmedEmailUser, self).__init__(message)


class RouteWithoutPermissions(PRException):
    def __init__(self, message='This is defined without permissions. You should not see that message'):
        super(RouteWithoutPermissions, self).__init__(message)


class Validation(PRException):
    def __init__(self, message='Validation error'):
        super(Validation, self).__init__(message)


class BadDataProvided(PRException):
    def __init__(self, message='Bad data provided'):
        super(BadDataProvided, self).__init__(message)


class NotAcceptedTOS(PRException):
    def __init__(self, message='Not accepted TOS', redirect_to=None):
        super(NotAcceptedTOS, self).__init__(message, redirect_to=redirect_to if redirect_to else
        url_for('index.welcome'))
