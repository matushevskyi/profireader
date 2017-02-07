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


class Permissions:
    _operator = 'or'
    _operands = []

    def __init__(self, operator='hahaha', *args):
        self._operands = args
        self._operator = operator

    def __and__(self, other):
        return Permissions('and', self, other)

    def __or__(self, other):
        return Permissions('or', self, other)

    def __neg__(self):
        return Permissions('not', self)

    def check(self, *args, **kwargs):
        if self._operator == 'and':
            return self._operands[0].check() and self._operands[1].check()
        elif self._operator == 'or':
            return self._operands[0].check() or self._operands[1].check()
        elif self._operator == 'not':
            return not self._operands[0].check()
        else:
            raise Exception('unknown operator')


class UserIsActive(Permissions):
    user_id = None
    user = None

    def check(self, *args, **kwargs):
        if 'user_id' in kwargs:
            self.user_id = kwargs['user_id']
        from ..models.users import User
        self.user = User.get(self.user_id) if self.user_id else g.user
        if not self.user:
            raise exceptions.NotLoggedInUser()
        if self.user.status != User.STATUSES['USER_ACTIVE']:
            raise exceptions.BannedUser()
        if not self.user.email_confirmed:
            raise exceptions.UnconfirmedEmailUser()
        return self.user


class CompanyIsActive(Permissions):
    company_id = None
    company = None

    def check(self, *args, **kwargs):
        from ..models.company import Company
        if 'company_id' in kwargs:
            self.company_id = kwargs['company_id']
        self.company = Company.get(self.company_id)

        if not self.company:
            raise Exception("No company found `%s`" % self.company_id)

        if not self.company.is_active():
            raise Exception("company `%s` is not active" % self.company_id)


class EmploymentIsActive(Permissions):
    user_is_active = None
    company_is_active = None
    employment = None

    def check(self, *args, **kwargs):
        self.company_is_active = CompanyIsActive()
        self.user_is_active = UserIsActive()


        self.user_is_active.check(*args, **kwargs)
        self.company_is_active.check(*args, **kwargs)

        from ..models.company import UserCompany
        self.employment = UserCompany.get_by_user_and_company_ids(user_id=self.user_is_active.user.id,
                                                                  company_id=self.company_is_active.company.id)

        if not self.employment:
            raise Exception("No employment found by user_id, company_id = {},{}".format(
                self.user_is_active.user.id, self.company_is_active.company.id))

        if not self.employment.is_active():
            raise Exception("employment `%s` is not active" % self.employment.id)


class EmployeeHasRight(Permissions):
    rights = None
    employment_is_active = None

    def __init__(self, right=RIGHT_AT_COMPANY._ANY):
        self.rights = right

    def check(self, *args, **kwargs):

        self.employment_is_active = EmploymentIsActive()
        self.employment_is_active.check(**kwargs)

        if RIGHT_AT_COMPANY._ANY == self.rights:
            return True

        elif RIGHT_AT_COMPANY._OWNER == self.rights:
            return self.employment_is_active.employment.company.user_owner.id == \
                   self.employment_is_active.employment.user_id

        else:
            return True if self.employment_is_active.employment.rights[self.rights] else False


class EmployeeHasRightAF(Permissions):
    load_right = None
    validate_right = None
    save_right = None

    employee_have_right = None
    __kwargs = None

    def __init__(self, **kwargs):
        self.__kwargs = kwargs
        self.load_right = kwargs.get('load', RIGHT_AT_COMPANY._ANY)
        self.validate_right = kwargs.get('validate', RIGHT_AT_COMPANY._ANY)
        self.save_right = kwargs.get('save', RIGHT_AT_COMPANY._OWNER)

    def check(self, json, *args, **kwargs):
        action = g.req('action', allowed=['load', 'validate', 'save'])

        right = getattr(self, action + '_right', None)

        if right is True or right is False:
            return right

        print(json)
        print(right)
        print(args)
        print(kwargs)

        EmployeeHasRight(right).check(*args, **kwargs)
        return True


class CheckFunction(Permissions):
    f = None

    def __init__(self, f):
        self.f = f

    def check(self, *args, **kwargs):
        return self.f()

#
# def employee_have_right(right=None):
#     def allowed(*args, **kwargs):
#         employment = employment_is_active(*args, **kwargs)
#         # aright = RIGHT_AT_COMPANY._ANY if right is None else right
#         if aright == RIGHT_AT_COMPANY._ANY:
#             return True
#         elif aright == RIGHT_AT_COMPANY._OWNER and employment.company.user_owner.id == employment.user_id:
#             return True
#         elif employment.rights[aright]:
#             return True
#         else:
#             return False
#
#     return allowed

#
# def employee_af(load=None, validate=None, save=None):
#     from ..models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
#     perm_for_actions = {
#         'load': RIGHT_AT_COMPANY._ANY if load is None else load,
#         'validate': RIGHT_AT_COMPANY._ANY if validate is None else validate,
#         'save': RIGHT_AT_COMPANY._OWNER if save is None else save,
#     }
#
#     def allowed(json, company_id, user_id=None):
#         user_id = g.user.id if user_id is None else user_id
#         action = g.req('action', allowed=['load', 'validate', 'save'])
#         if action not in perm_for_actions:
#             raise Exception('action should be one of `' + '`,`'.join(perm_for_actions.keys()) + "`")
#
#         if perm_for_actions[action] is True or perm_for_actions[action] is False:
#             return perm_for_actions[action]
#
#         return employment_is_active(user_id=user_id, company_id=company_id)
#
#     return allowed
