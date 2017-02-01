from ..models import exceptions
from flask import g


class BinaryRightsMetaClass(type):
    def _allrights(self):
        return {name: type.__getattribute__(self, name) for (name, val) in
                self.__dict__.items() if name not in ['__doc__', '__module__', '_nice_order']}

    def _todict(self, bin):
        from collections import OrderedDict
        ret = OrderedDict()

        rights = {name: (True if ((1 << type.__getattribute__(self, name)) & bin) else False) for (name, val) in
                self._allrights().items()}
        n_order = self._nice_order(self)

        for key in n_order:
            ret[key] = rights[key]
        for key in rights:
            if key not in ret:
                ret[key] = rights[key]
        return ret

    def _tobin(self, dict):
        ret = 0
        all_rights = self._allrights()
        for (rightname, truefalse) in dict.items():
            if rightname == self._OWNER and truefalse:  # any right
                ret = 0x7fffffffffffffff
            else:
                bit_position = all_rights.get(rightname)
                if bit_position is None:
                    raise Exception(
                        "right `{}` doesn't exists in allowed columns rights: {}".format(rightname,
                                                                                         self._allrights()))
                else:
                    ret |= (1 << bit_position) if truefalse else 0

        return ret


    def _totext(self, dict):
        ret = 0
        all_rights = self._allrights()
        for (rightname, truefalse) in dict.items():
            if rightname == self._OWNER and truefalse:  # any right
                ret = 0x7fffffffffffffff
            else:
                bit_position = all_rights.get(rightname)
                if bit_position is None:
                    raise Exception(
                        "right `{}` doesn't exists in allowed columns rights: {}".format(rightname,
                                                                                         self._allrights()))
                else:
                    ret |= (1 << bit_position) if truefalse else 0

        return ret


    def __getattribute__(self, key):
        if key in ['_todict', '_tobin', '_allrights', '_nice_order'] or (key[:2] == '__' and key[-2:] == '__'):
            return type.__getattribute__(self, key)
        elif key in type.__getattribute__(self, '_allrights')():
            return key
        elif key in ['_OWNER', '_ANY']:
            return key
        else:
            raise Exception(
                "right `{}` doesn't exists in allowed columns rights: {}".format(key,
                                                                                 self._allrights()))


class BinaryRights(metaclass=BinaryRightsMetaClass):
    _OWNER = -1
    _ANY = -2

    def _nice_order(self):
        return []


class RIGHT_AT_COMPANY(BinaryRights):
    FILES_BROWSE = 4
    FILES_UPLOAD = 5
    FILES_DELETE_OTHERS = 14

    ARTICLES_SUBMIT_OR_PUBLISH = 8
    ARTICLES_UNPUBLISH = 17  # reset!
    ARTICLES_EDIT_OTHERS = 12
    ARTICLES_DELETE = 19  # reset!

    COMPANY_EDIT_PROFILE = 1
    COMPANY_MANAGE_PARTICIPATION = 2
    COMPANY_REQUIRE_MEMBEREE_AT_PORTALS = 15

    EMPLOYEE_ENLIST_OR_FIRE = 6
    EMPLOYEE_ALLOW_RIGHTS = 9

    PORTAL_EDIT_PROFILE = 10
    PORTAL_MANAGE_READERS = 16
    PORTAL_MANAGE_COMMENTS = 18
    PORTAL_MANAGE_MEMBERS_COMPANIES = 13

    def _nice_order(self):
        return [
            self.COMPANY_EDIT_PROFILE, self.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS, self.COMPANY_MANAGE_PARTICIPATION,
            self.EMPLOYEE_ENLIST_OR_FIRE, self.EMPLOYEE_ALLOW_RIGHTS,
            self.ARTICLES_SUBMIT_OR_PUBLISH, self.ARTICLES_UNPUBLISH, self.ARTICLES_EDIT_OTHERS,
            self.ARTICLES_DELETE,
            self.FILES_BROWSE, self.FILES_UPLOAD, self.FILES_DELETE_OTHERS,
            self.PORTAL_EDIT_PROFILE, self.PORTAL_MANAGE_READERS, self.PORTAL_MANAGE_COMMENTS,
            self.PORTAL_MANAGE_MEMBERS_COMPANIES,
        ]


class RIGHT_AT_PORTAL(BinaryRights):
    PUBLICATION_PUBLISH = 1
    PUBLICATION_UNPUBLISH = 2

    def _nice_order(self):
            return [self.PUBLICATION_PUBLISH, self.PUBLICATION_UNPUBLISH]

def user_is_active(*args, **kwargs):
    from ..models.users import User
    if 'user_id' in kwargs:
        user = User.get(kwargs['user_id'])
    else:
        if not getattr(g, 'user', False) or not getattr(g.user, 'id', False):
            raise exceptions.NotLoggedInUser()
        user = g.user
    if user.status != User.STATUSES['USER_ACTIVE']:
        raise exceptions.BannedUser()
    if not user.email_confirmed:
        raise exceptions.UnconfirmedEmailUser()
    return user


def company_is_active(*args, **kwargs):
    from ..models.company import Company

    company = Company.get(kwargs.get('company_id', ''), returnNoneIfNotExists=True)
    if not company:
        raise Exception("No company found `%s`" % kwargs.get('company_id', ''))

    if not company.is_active():
        raise Exception("company `%s` is not active" % company.id)

    return company


def employment_is_active(*args, **kwargs):
    from ..models.company import UserCompany

    user = user_is_active(kwargs)
    employment = UserCompany.get_by_user_and_company_ids(user_id=user.id, company_id=kwargs.get('company_id', ''))

    if not employment:
        raise Exception("No employment found by company_id and user_id")

    if not employment.is_active():
        raise Exception("employment `%s` is not active" % employment.id)

    return employment


def employee_have_right(right=None):

    def allowed(*args, **kwargs):
        employment = employment_is_active(*args, **kwargs)
        aright = RIGHT_AT_COMPANY._ANY if right is None else right
        if aright == RIGHT_AT_COMPANY._ANY:
            return True
        elif aright == RIGHT_AT_COMPANY._OWNER and employment.company.user_owner.id == employment.user_id:
            return True
        elif employment.rights[aright]:
            return True
        else:
            return False

    return allowed


def employee_af(load=None, validate=None, save=None):
    from ..models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
    perm_for_actions = {
        'load': RIGHT_AT_COMPANY._ANY if load is None else load,
        'validate': RIGHT_AT_COMPANY._ANY if validate is None else validate,
        'save': RIGHT_AT_COMPANY._OWNER if save is None else save,
    }

    def allowed(json, company_id, user_id=None):
        user_id = g.user.id if user_id is None else user_id
        action = g.req('action', allowed=['load', 'validate', 'save'])
        if action not in perm_for_actions:
            raise Exception('action should be one of `' + '`,`'.join(perm_for_actions.keys()) + "`")

        if perm_for_actions[action] is True or perm_for_actions[action] is False:
            return perm_for_actions[action]

        return employment_is_active(user_id=user_id, company_id=company_id)

    return allowed



