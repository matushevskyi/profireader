from ..models import exceptions
from flask import g


class BasePermissionChecker:
    def check_permissions(self):
        raise Exception('Please define check_permissions in class')


class IsUserActive(BasePermissionChecker):
    def check_permissions(self):
        if not getattr(g, 'user', False) or not getattr(g.user, 'id', False):
            raise exceptions.NotLoggedInUser()
        if g.user.banned:
            raise exceptions.BannedUser()
        if g.user.email_confirmed:
            raise exceptions.UnconfirmedEmailUser()
