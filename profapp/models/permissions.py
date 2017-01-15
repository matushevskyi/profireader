from ..models import exceptions
from flask import g


class BasePermissionChecker:
    def __init__(self, *args, **kwargs):
        raise Exception('Please define check_permissions in class')



class IsUserActive(BasePermissionChecker):
    def __init__(self, *args, **kwargs):
        if not getattr(g, 'user', False) or not getattr(g.user, 'id', False):
            raise exceptions.NotLoggedInUser()
        if g.user.banned:
            raise exceptions.BannedUser()
        if not g.user.email_confirmed:
            raise exceptions.UnconfirmedEmailUser()
