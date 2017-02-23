from ..models import exceptions
from flask import g
from profapp import utils


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
    _operator = 'hihi'
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
            return self._operands[0].check(*args, **kwargs) and self._operands[1].check(*args, **kwargs)
        elif self._operator == 'or':
            return self._operands[0].check(*args, **kwargs) or self._operands[1].check(*args, **kwargs)
        elif self._operator == 'not':
            return not self._operands[0].check(*args, **kwargs)
        else:
            raise Exception('unknown operator')

        return True


class AvailableForAll(Permissions):
    def __init__(self, *args, **kwargs):
        pass

    def check(self, *args, **kwargs):
        return True


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

        return True


class UserIsAdmin(UserIsActive):
    def check(self, *args, **kwargs):
        del kwargs['user_id']
        return super(UserIsAdmin, self).check(*args, **kwargs) and self.user.is_admin()


class UserIsMaintainer(UserIsActive):
    def check(self, *args, **kwargs):
        del kwargs['user_id']
        return super(UserIsMaintainer, self).check(*args, **kwargs) and self.user.is_maintainer(or_admin=False)


class UserIsAdminOrMaintainer(UserIsActive):
    def check(self, *args, **kwargs):
        del kwargs['user_id']
        return super(UserIsAdminOrMaintainer, self).check(*args, **kwargs) and self.user.is_maintainer(or_admin=True)


class UserIsOwner(UserIsActive):
    def check(self, *args, **kwargs):
        return super(UserIsOwner, self).check(*args, **kwargs) and g.user.id == kwargs['user_id']


class CompanyIsActive(Permissions):
    company_id = None
    company = None

    def check(self, *args, **kwargs):
        from ..models.company import Company
        if 'company_id' in kwargs:
            self.company_id = kwargs['company_id']
        self.company = Company.get(self.company_id, returnNoneIfNotExists=True)

        if not self.company:
            raise Exception("No company found `%s`" % self.company_id)

        if not self.company.is_active():
            raise Exception("company `%s` is not active" % self.company_id)

        return True


class PortalIsActive(Permissions):
    portal_id = None
    portal = None

    def check(self, *args, **kwargs):
        return True
        from ..models.company import Portal
        if 'portal_id' in kwargs:
            self.portal_id = kwargs['portal_id']
        self.portal = Portal.get(self.portal_id, returnNoneIfNotExists = True)
        if not self.portal:
            raise Exception("No portal found `%s`" % self.portal_id)

        company_is_active = CompanyIsActive()
        company_is_active.check(company_id=self.portal.company_owner_id)

        if not self.portal.is_active():
            raise Exception("portal `%s` is not active" % self.portal_id)

        return True


class EmploymentIsActive(Permissions):
    employment = None

    def check(self, *args, **kwargs):
        company_is_active = CompanyIsActive()
        user_is_active = UserIsActive()

        user_is_active.check(*args, **kwargs)
        company_is_active.check(*args, **kwargs)

        from ..models.company import UserCompany
        self.employment = UserCompany.get_by_user_and_company_ids(
            user_id=user_is_active.user.id, company_id=company_is_active.company.id)

        if not self.employment:
            raise Exception("No employment found by user_id, company_id = {},{}".format(
                user_is_active.user.id, company_is_active.company.id))

        if not self.employment.is_active():
            raise Exception("employment `%s` is not active" % self.employment.id)

        return True


class MembershipIsActive(Permissions):
    membership_id = None
    membership = None

    def check(self, membership_id):
        from ..models.portal import MemberCompanyPortal
        self.membership_id = membership_id
        self.membership = MemberCompanyPortal.get(self.membership_id, returnNoneIfNotExists = True)

        if not self.membership:
            raise Exception("No membership found by user_id, company_id = {},{}".format(self.membership_id))

        if not self.membership.is_active():
            raise Exception("membership `%s` is not active" % self.membership.id)

        portal_is_active = PortalIsActive()
        portal_is_active.check(portal_id=self.membership.portal_id)

        company_is_active = CompanyIsActive()
        company_is_active.check(company_id=self.membership.company_id)

        return True


class EmployeeHasRightAtCompany(Permissions):
    rights = None

    def __init__(self, right=RIGHT_AT_COMPANY._ANY):
        self.rights = right

    def check(self, *args, **kwargs):

        employment_is_active = EmploymentIsActive()
        employment_is_active.check(**kwargs)
        employment = employment_is_active.employment

        if RIGHT_AT_COMPANY._ANY == self.rights:
            return True

        elif RIGHT_AT_COMPANY._OWNER == self.rights:
            return employment.company.user_owner.id == employment.user_id

        else:
            return True if employment.rights[self.rights] else False


class EmployeeHasRightAtPortalOwnCompany(EmployeeHasRightAtCompany):
    def check(self, *args, **kwargs):
        from profapp.models.portal import Portal, MemberCompanyPortal
        if 'portal_id' in kwargs:
            portal = Portal.get(kwargs['portal_id'])
        elif 'membership_id' in kwargs:
            portal = MemberCompanyPortal.get(kwargs['membership_id']).portal
        else:
            raise Exception("No portal found by portal_id or membership_id kwargs={}".format(kwargs))

        kwargs['company_id'] = portal.company_owner_id
        return super(EmployeeHasRightAtPortalOwnCompany, self).check(*args, **kwargs) and portal.is_active()


class EmployeeHasRightAtMembershipCompany(Permissions):
    rights = None

    def __init__(self, right=RIGHT_AT_COMPANY._ANY):
        self.rights = right

    def check(self, *args, **kwargs):
        membership_is_active = MembershipIsActive()
        membership_is_active.check(kwargs['membership_id'])
        employee_has_right = EmployeeHasRightAtCompany(self.rights)
        return employee_has_right.check(company_id=membership_is_active.membership.company_id)


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

        EmployeeHasRightAtCompany(right).check(*args, **kwargs)
        return True


class CheckFunction(Permissions):
    f = None

    def __init__(self, f):
        self.f = f

    def check(self, *args, **kwargs):
        return self.f()


class ActionsForMaterialAtMembership(Permissions):
    _action = None

    ACTIONS = {'DELETE': 'DELETE', 'SUBMIT': 'SUBMIT', 'UNDELETE': 'UNDELETE'}

    def __init__(self, action):
        self._action = action

    def check(self, membership_id, material_id):
        from profapp.models.portal import MemberCompanyPortal
        from profapp.models.materials import Material
        from profapp import utils

        membership = MemberCompanyPortal.get(membership_id)

        action = utils.find_by_keys(self.actions(membership, material=Material.get(material_id)), self._action, 'name')

        if not action:
            raise Exception("Unknown action {} for membership={}, material={}".format(
                self._action, membership_id, material_id))

        return action['enabled'] is True

    @classmethod
    def actions(cls, membership, material, check_only_for_action=None):
        from profapp.models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
        from ..models.company import UserCompany

        employment = UserCompany.get_by_user_and_company_ids(company_id=material.company_id)

        ret = [
            {'name': cls.ACTIONS['SUBMIT'], 'enabled': employment.rights[RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH]}
        ]

        for change in ret:
            change['message'] = ''

        if check_only_for_action:
            return True if utils.find_by_keys(ret, check_only_for_action, 'name') else False
        else:
            return ret


class ActionsForPublicationAtMembership(Permissions):
    _action = None

    ACTIONS = {
        'DELETE': 'DELETE', 'UNPUBLISH': 'UNPUBLISH', 'UNDELETE': 'UNDELETE', 'PUBLISH': 'PUBLISH'}

    def __init__(self, action):
        self._action = action

    def check(self, membership_id, publication_id):
        from profapp.models.portal import MemberCompanyPortal
        from profapp.models.materials import Material, Publication
        from profapp import utils

        membership = MemberCompanyPortal.get(membership_id)

        action = utils.find_by_keys(self.actions(
            membership, publication=Publication.get(publication_id, True)), self._action, 'name')

        if not action:
            raise Exception("Unknown action {} for membership={}, publication={}".format(
                self._action, membership_id, publication_id))

        return action['enabled'] is True

    @classmethod
    def actions(cls, membership, publication):
        from profapp.models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
        from ..models.company import UserCompany
        from ..models.materials import Publication

        employment = UserCompany.get_by_user_and_company_ids(company_id=membership.company_id)

        publish_rights = employment.rights[RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH] and \
                         membership.rights[RIGHT_AT_PORTAL.PUBLICATION_PUBLISH]

        unpublish_rights = employment.rights[RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH] and \
                           membership.rights[RIGHT_AT_PORTAL.PUBLICATION_UNPUBLISH]

        if publication.status == Publication.STATUSES['SUBMITTED']:
            ret = [
                {'name': cls.ACTIONS['DELETE'], 'enabled': employment.rights[RIGHT_AT_COMPANY.ARTICLES_DELETE]},
                {'name': cls.ACTIONS['PUBLISH'], 'enabled': publish_rights},
            ]
        elif publication.status == Publication.STATUSES['UNPUBLISHED']:
            ret = [
                {'name': cls.ACTIONS['DELETE'], 'enabled': employment.rights[RIGHT_AT_COMPANY.ARTICLES_DELETE]},
                {'name': cls.ACTIONS['PUBLISH'], 'enabled': publish_rights},
            ]
        elif publication.status == Publication.STATUSES['PUBLISHED']:
            ret = [
                {'name': cls.ACTIONS['UNPUBLISH'], 'enabled': unpublish_rights},
                {'name': cls.ACTIONS['PUBLISH'], 'enabled': publish_rights and unpublish_rights},
            ]
        elif publication.status == Publication.STATUSES['DELETED']:
            ret = [
                {'name': cls.ACTIONS['UNDELETE'], 'enabled': unpublish_rights},
            ]
        else:
            ret = []

        for change in ret:
            change['message'] = ''

        return ret

    @classmethod
    def article_actions_by_portal(cls, publication):
        from profapp.models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
        from ..models.company import UserCompany
        from ..models.portal import MemberCompanyPortal
        from ..models.materials import Publication

        portal = publication.portal_division.portal
        employment = UserCompany.get_by_user_and_company_ids(company_id=portal.company_owner_id)
        membership = MemberCompanyPortal.get_by_portal_id_company_id(
            portal_id=portal.id, company_id=portal.company_owner_id)

        publish_rights = employment.rights[RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH] and \
                         membership.rights[RIGHT_AT_PORTAL.PUBLICATION_PUBLISH]

        unpublish_rights = employment.rights[RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH] and \
                           membership.rights[RIGHT_AT_PORTAL.PUBLICATION_UNPUBLISH]

        if publication.status == Publication.STATUSES['SUBMITTED']:
            ret = [
                {'name': cls.ACTIONS['DELETE'], 'enabled': employment.rights[RIGHT_AT_COMPANY.ARTICLES_DELETE]},
            ]
        elif publication.status == Publication.STATUSES['UNPUBLISHED']:
            ret = [
                {'name': cls.ACTIONS['DELETE'], 'enabled': employment.rights[RIGHT_AT_COMPANY.ARTICLES_DELETE]},
                {'name': cls.ACTIONS['PUBLISH'], 'enabled': publish_rights},
            ]
        elif publication.status == Publication.STATUSES['PUBLISHED']:
            ret = [
                {'name': cls.ACTIONS['UNPUBLISH'], 'enabled': unpublish_rights},
                {'name': cls.ACTIONS['PUBLISH'], 'enabled': publish_rights and unpublish_rights},
            ]
        elif publication.status == Publication.STATUSES['DELETED']:
            ret = [
                {'name': cls.ACTIONS['UNDELETE'], 'enabled': unpublish_rights},
            ]
        else:
            ret = []

        for change in ret:
            change['message'] = ''
        return ret


class ActionsForFileManagerAtMembership(Permissions):
    _action = None

    ACTIONS = {
        'DOWNLOAD': 'download',
        'REMOVE': 'remove',
        'CUT': 'cut',
        'PROPERTIES': 'properties',
        'PASTE': 'paste',
        'COPY': 'copy',
        'CHOOSE': 'choose'
    }

    def __init__(self, action):
        self._action = action

    def check(self, membership_id):
        from profapp.models.portal import MemberCompanyPortal
        from profapp import utils

        membership = MemberCompanyPortal.get(membership_id)

        action = utils.find_by_keys(self.actions(membership), self._action, 'name')

        if not action:
            raise Exception("Unknown action {} for membership={}, publication={}".format(
                self._action, membership_id))

        return action['enabled'] is True

    # @staticmethod
    # def base_actions(self, *args, object=None, **kwargs):
    #     if not isinstance(object, str) and not hasattr(object, 'status'):
    #         raise Exception('Bad data!')
    #     return {action_name: self.action_is_allowed(action_name, *args, **kwargs) for action_name
    #             in self.ACTIONS_FOR_STATUSES[object.status if not isinstance(object, str) else object]}

    @classmethod
    # TODO: OZ by OZ: convert this actions as in another Actions classes
    def actions(cls, file, called_for):
        import re
        actions = {}
        if not file:
            raise Exception('Bad data!')

        for a in cls.ACTIONS:
            actions[cls.ACTIONS[a]] = True

        if file.mime in ['directory', 'root']:
            del actions['download']
        else:
            del actions['paste']

        if called_for == 'file_browse_image':
            actions['choose'] = re.search('^image/.*', file.mime) is not None
        elif called_for == 'file_browse_media':
            actions['choose'] = re.search('^video/.*', file.mime) is not None
        elif called_for == 'file_browse_file':
            actions['choose'] = True
        else:
            del actions['choose']

        return actions

    @classmethod
    def file_actions_by_membership(cls, actionname, file):
        return True

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
