

class NotLoggedInUser(Exception):
    def __init__(self, message='User is not logged in. Please log in'):
        super(NotLoggedInUser, self).__init__(message)


class BannedUser(Exception):
    def __init__(self, message='User is baned. pls contact administrator'):
        super(BannedUser, self).__init__(message)


class UnauthorizedUser(Exception):
    def __init__(self, message='User is unauthorized to do this. go away'):
        super(UnauthorizedUser, self).__init__(message)


class UnconfirmedEmailUser(Exception):
    def __init__(self, message='Email is unconfirmed. pls confirm email'):
        super(UnconfirmedEmailUser, self).__init__(message)


class RouteWithoutPermissions(Exception):
    def __init__(self, message='This is defined without permissions. You should not see that message'):
        super(RouteWithoutPermissions, self).__init__(message)


