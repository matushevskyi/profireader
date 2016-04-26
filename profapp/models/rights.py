from functools import reduce
import inspect
from flask import g
from utils.db_utils import db
from ..models.company import Company, UserCompany, MemberCompanyPortal
from ..models.portal import Portal, PortalDivision
from ..models.articles import ArticlePortalDivision, ArticleCompany
from ..models.users import User
from .pr_base import PRBase

#COMPANY_OWNER = ['edit', 'publish', 'unpublish', 'upload_files', 'delete_files', 'add_employee',
#                 'suspend_employee', 'submit_publications', 'manage_rights_company', 'manage_portal',
#                 'article_priority', 'manage_readers', 'manage_companies_members', 'manage_comments',
#                 'subscribe_to_portals']


# ROLE = {
#     OWNER: 'owner',
#     ADMIN: 'admin',
#     EDITOR: 'editor',
#     STAFF: 'staff',
#     CONTRIBUTOR: 'contributor',
#     USER: 'user',
#     GUEST: 'guest',
#     READER: 'reader'
# }
class BaseRightsInProfireader:

    user_rights = UserCompany.RIGHT_AT_COMPANY

    ACTIONS = {
        'CREATE_COMPANY': 'CREATE_COMPANY',
        'EDIT_USER_PROFILE': 'EDIT_USER_PROFILE',
        'SUBSCRIBE_TO_PORTAL': 'SUBSCRIBE_TO_PORTAL',
    }

    def __setattr__(self, key, value):

        if key == 'company_id':
            key = 'company'
            if isinstance(value, str):
                value = Company.get(value)
        if key == 'employment_id':
            key = 'employment'
            if isinstance(value, str):
                value = db(UserCompany, id=value).first()
        object.__setattr__(self, key, value)

    def check_objects_statuses(self, objects, action_name):
        user_active = g.user.is_active()
        if user_active != True:
            return user_active
        for key in objects:
            if not objects[key]:
                return "Unconfirmed {}!".format(key)
            if objects[key].is_active() != True:
                return "{} should be active to perform action `{}`".format(key, action_name)
        return True

    def check_rights(self, action_name, necessary_rights, objects_for_check):
        if isinstance(necessary_rights, tuple):
            _any = []
            message = ''
            for elements in necessary_rights:
                for object in elements:
                    if isinstance(elements[object], str):
                        if objects_for_check[object].has_rights(elements[object]) != True:
                            _any.append(False)
                            message = "{} need right `{}` to perform action `{}`".format(object, elements[object],
                                                                                                action_name)
                        else:
                            _any.append(True)
                    else:
                        if not elements[object](objects_for_check[object]):
                            _any.append(False)
                        else:
                            _any.append(True)
            if any(_any):
                return True
            else:
                return message
        else:
            for object in necessary_rights:
                if callable(necessary_rights[object]):
                    result = necessary_rights[object](objects_for_check[object])
                    if result != True:
                        return "{} need right `{}` to perform action `{}`".format(object, result, action_name)
                elif isinstance(necessary_rights[object], list):
                    for right in necessary_rights[object]:
                        if objects_for_check[object].has_rights(right) != True:
                            return "{} need right `{}` to perform action `{}`".format(object, right, action_name)
                elif objects_for_check[object].has_rights(necessary_rights[object]) != True:
                    return "{} need right `{}` to perform action `{}`".format(object, necessary_rights[object],
                                                                              action_name)
        return True

    @staticmethod
    def _is_action_allowed(self, action_name, objects_for_check_status, objects_for_check_rights, actions=None, actions_for_statuses=None):
        required_rights = None
        if not action_name in actions:
            return "Unrecognized action `{}`".format(action_name)

        if not self.status in actions_for_statuses:
            return "Unrecognized status `{}`".format(self.status)

        if not action_name in actions_for_statuses[self.status]:
            return "Action `{}` is not applicable for publication with status `{}`".format(action_name,
                                                                                           self.status)
        check_status_in_objects = BaseRightsInProfireader().check_objects_statuses(objects_for_check_status, action_name)
        if check_status_in_objects != True:
            return check_status_in_objects

        if self.status in actions_for_statuses:
            required_rights = actions_for_statuses[self.status][action_name]

        result = BaseRightsInProfireader().check_rights(action_name, required_rights, objects_for_check_rights)
        if result != True:
            return result

        return True

    @staticmethod
    def base_actions(self, *args, status=None):
        return {action_name: self.action_is_allowed(action_name, *args) for action_name
                in self.ACTIONS_FOR_STATUSES[status]}


class PublishUnpublishInPortal(BaseRightsInProfireader):

        def __init__(self, publication, division=None, company=None):
            self.publication = publication if isinstance(publication, ArticlePortalDivision) else ArticlePortalDivision.get(publication)
            self.division = division if isinstance(division, PortalDivision) else PortalDivision.get(division) if division else None
            self.company = company if isinstance(company, Company) else Company.get(company) if company else None

        STATUSES = ArticlePortalDivision.STATUSES
        ACTIONS = {
            'PUBLISH': 'PUBLISH',
            'UNPUBLISH': 'UNPUBLISH',
            'EDIT': 'EDIT',
            'REPUBLISH': 'REPUBLISH',
            'DELETE': 'DELETE',
            'UNDELETE': 'UNDELETE'
        }

        delete_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL._OWNER],
                         'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_DELETE]}

        publish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL._OWNER],
                          'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_DELETE]}

        unpublish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_UNPUBLISH],
                            'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH]}

        republish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH,
                                           MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_UNPUBLISH],
                            'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH,
                                           UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH]}

        ACTIONS_FOR_STATUSES = {
            STATUSES['SUBMITTED']: {
                ACTIONS['PUBLISH']: publish_rights,
                ACTIONS['DELETE']: delete_rights,
            },
            STATUSES['PUBLISHED']: {
                ACTIONS['REPUBLISH']: republish_rights,
                ACTIONS['UNPUBLISH']: unpublish_rights,
                ACTIONS['EDIT']: publish_rights,
                ACTIONS['DELETE']: delete_rights
            },
            STATUSES['UNPUBLISHED']: {
                ACTIONS['REPUBLISH']: publish_rights,
                ACTIONS['EDIT']: republish_rights,
                ACTIONS['DELETE']: delete_rights
            },
            STATUSES['DELETED']: {
                ACTIONS['UNDELETE']: delete_rights,
            }
        }
        def actions(self):
            return BaseRightsInProfireader.base_actions(self, status=self.publication.status)

        def action_is_allowed(self, action_name):
            company = self.company if self.company else self.division.portal.own_company
            employee = UserCompany.get(company_id=company.id)
            membership = MemberCompanyPortal.get(portal_id=self.division.portal.id, company_id=company.id)
            company_object = self.publication.company
            check_objects_status = {'employeer':company,
                                    'employee': employee,
                                    'membership': membership,
                                    'company where you want update publication': company_object,
                                    'division':self.division}

            return BaseRightsInProfireader._is_action_allowed(self.publication, action_name,
                        check_objects_status, {'employment': employee, 'membership': membership},
                        actions=self.ACTIONS, actions_for_statuses=self.ACTIONS_FOR_STATUSES)

class EditOrSubmitMaterialInPortal(BaseRightsInProfireader):

    def __init__(self, material, portal=None, division=None):
        self.material = material if isinstance(material, ArticleCompany) else ArticleCompany.get(material)
        self.employee = UserCompany.get(company_id=self.material.company.id)
        self.portal = portal if isinstance(portal, Portal) else Portal.get(portal) if portal else None
        self.division = division if isinstance(division, PortalDivision) else PortalDivision.get(division) if division else None

    ACTIONS = {
        'SUBMIT': 'SUBMIT',
        'EDIT': 'EDIT'
    }
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    ACTIONS_FOR_STATUSES = {
        STATUSES['NORMAL']: {
            ACTIONS['SUBMIT']:
                {'employee': UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH,
                 'membership': MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH},
            ACTIONS['EDIT']: (
                {'employee': UserCompany.RIGHT_AT_COMPANY.ARTICLES_EDIT_OTHERS},
                {'articleowner':lambda kwarg: kwarg['material'].editor_user_id == kwarg['user'].id or False})
        }
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, status=self.material.status)

    def action_is_allowed(self, action_name):
        check_objects_status = {'company owner material': self.material.company,
                                'employee': self.employee}

        check_objects_status.update({'division':self.division}) if self.division else None

        check_objects_rights = {'company owner material': self.material.company,
                                'employee': self.employee, 'articleowner': {'material': self.material, 'user': g.user}}
        if self.portal:
            check_objects_rights.update({'membership': MemberCompanyPortal.get(portal_id=self.portal.id, company_id=self.material.company.id)})
            check_objects_status.update({'membership': MemberCompanyPortal.get(portal_id=self.portal.id,
                                                                               company_id=self.material.company.id),
                                         'company where you want submit material': self.portal.own_company})

        return BaseRightsInProfireader._is_action_allowed(self.material, action_name,
                check_objects_status, check_objects_rights, actions=self.ACTIONS, actions_for_statuses=self.ACTIONS_FOR_STATUSES)

class BaseRightsEmployeeInCompany(BaseRightsInProfireader):

    def __init__(self, company=None, employment=None, member_company=None, material=None, user_id=None):
        self.company = company if isinstance(company, Company) else Company.get(company) if company else None
        self.employment = employment if isinstance(employment, UserCompany) else UserCompany.get(user_id=employment,company_id=self.company.id) if employment and company else None
        self.member_company = member_company
        self.material = material if isinstance(material, ArticleCompany) else ArticleCompany.get(material) if material else None
        self.user_id = user_id

    ACTIONS = {
        'EDIT_COMPANY': 'EDIT_COMPANY',
        'EDIT_PORTAL': 'EDIT_PORTAL',
        'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS':'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS',
        'PORTAL_MANAGE_MEMBERS_COMPANIES': 'PORTAL_MANAGE_MEMBERS_COMPANIES',
        'EMPLOYEE_ALLOW_RIGHTS': 'EMPLOYEE_ALLOW_RIGHTS'
    }

    ACTIONS_FOR_EMPLOYEE_IN_COMPANY = {
        'ACTIVE': {
            ACTIONS['EDIT_COMPANY']: {'employee': UserCompany.RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE},
            ACTIONS['EDIT_PORTAL']: {'employee': UserCompany.RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE},
            ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS']: {'employee': UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
            ACTIONS['PORTAL_MANAGE_MEMBERS_COMPANIES']:{'employee': UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
            ACTIONS['EMPLOYEE_ALLOW_RIGHTS']: {'employee': UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS}
        }
    }

    def is_action_allowed(self, action):
        employee = UserCompany.get(company_id=self.company.id)
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company}
        return BaseRightsInProfireader._is_action_allowed(employee, action,
                                                          get_objects_for_check, {'employee': employee},
                                                          actions=BaseRightsEmployeeInCompany.ACTIONS,
                                                          actions_for_statuses=BaseRightsEmployeeInCompany.ACTIONS_FOR_EMPLOYEE_IN_COMPANY)

class FilemanagerRights(BaseRightsEmployeeInCompany):

    ACTIONS = {
        'DOWNLOAD': 'DOWNLOAD',
        'REMOVE': 'REMOVE',
        'SHOW': 'SHOW',
        'UPLOAD': 'UPLOAD',
        'CUT': 'CUT',
        'CREATE_FOLDER': 'CREATE_FOLDER'
    }
    ACTIONS_FOR_FILEMANAGER = {
        'ACTIVE': {
            ACTIONS['DOWNLOAD']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE},
            ACTIONS['REMOVE']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS},
            ACTIONS['SHOW']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE},
            ACTIONS['UPLOAD']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD},
            ACTIONS['CUT']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS},
            ACTIONS['CREATE_FOLDER']: {'employee': UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD}
        }
    }

    def is_action_allowed(self, action):
        employee = UserCompany.get(company_id=self.company.id)
        if employee:
            get_objects_for_check = {'employee': employee,
                                     'employeer': self.company}
            result = BaseRightsInProfireader._is_action_allowed(employee, action, get_objects_for_check, {'employee': employee},
                                                              actions=FilemanagerRights.ACTIONS,
                                                              actions_for_statuses=FilemanagerRights.ACTIONS_FOR_FILEMANAGER)
            if result != True:
                return result
        elif not employee and action != FilemanagerRights.ACTIONS['SHOW']:
            return "You cannot menage files in joined company!"
        return True



class EmployeesRight(BaseRightsEmployeeInCompany):

    STATUSES = UserCompany.STATUSES

    ACTIONS = {
        'ENLIST': 'ENLIST',
        'REJECT': 'REJECT',
        'FIRE': 'FIRE',
        'ALLOW': 'ALLOW'
    }

    ACTIONS_FOR_STATUSES = {
        STATUSES['APPLICANT']: {
            ACTIONS['ENLIST']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
            ACTIONS['REJECT']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },
        STATUSES['REJECTED']: {
            ACTIONS['ENLIST']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },

        STATUSES['FIRED']: {
            ACTIONS['ENLIST']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },
        STATUSES['ACTIVE']: {
            ACTIONS['FIRE']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
            ACTIONS['ALLOW']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS]},
        }
    }

    def action_is_allowed(self, action_name):
        employee = UserCompany.get(company_id=self.company.id)
        if action_name == 'FIRE':
                if self.employment.user_id == employee.employer.author_user_id:
                    return 'You can`t fire company owner'

        if action_name == 'ALLOW':
                if self.employment.user_id == employee.employer.author_user_id:
                    return 'Company owner have all permissions and you can do nothing with that'
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company,
                                 'user':self.employment.employee}
        return BaseRightsInProfireader._is_action_allowed(self.employment, action_name,
                get_objects_for_check, {'employee': employee},actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, status=self.employment.status)


class MembersOrMembershipBase(BaseRightsEmployeeInCompany):
    STATUSES = MemberCompanyPortal.STATUSES
    INITIALLY_FILTERED_OUT_STATUSES = [STATUSES['DELETED'], STATUSES['REJECTED']]
    MEMBER = 'member'
    MEMBERSHIP = 'membership'

    ACTIONS = {
        'UNSUBSCRIBE': 'UNSUBSCRIBE',
        'FREEZE': 'FREEZE',
        'WITHDRAW': 'WITHDRAW',
        'RESTORE': 'RESTORE',
        'REJECT': 'REJECT',
        'SUSPEND': 'SUSPEND',
        'ENLIST': 'ENLIST',
        'ALLOW': 'ALLOW'
    }

    STATUS_FOR_ACTION = {
        ACTIONS['UNSUBSCRIBE']: STATUSES['DELETED'],
        ACTIONS['FREEZE']: STATUSES['FROZEN'],
        ACTIONS['WITHDRAW']: STATUSES['DELETED'],
        ACTIONS['REJECT']: STATUSES['REJECTED'],
        ACTIONS['SUSPEND']: STATUSES['SUSPENDED'],
        ACTIONS['ENLIST']: STATUSES['ACTIVE'],
        ACTIONS['RESTORE']: STATUSES['ACTIVE']
    }

    def action_is_allowed_member_company(self, action_name, employee, add_to_check_statuses=None):
        if self.member_company.portal.company_owner_id == self.member_company.company_id:
            return 'You can`t {0} portal of your own company'.format(action_name)
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company}
        if add_to_check_statuses:
            get_objects_for_check.update(add_to_check_statuses)
        return BaseRightsInProfireader._is_action_allowed(self.member_company, action_name,
                                                      get_objects_for_check, {'employee': employee},
                                                      actions=self.ACTIONS,
                                                      actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    def can_update_company_partner(self):
        user_right = UserCompany.get(company_id=self.company.id).has_rights(
            UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES)
        if self.member_company.status == MembersOrMembershipBase.STATUSES['FROZEN'] and not user_right:
            return 'Sorry!You can not manage company {}!It was frozen!'.format(self.company.name)
        if self.member_company.status == MembersOrMembershipBase.STATUSES['DELETED']:
            return 'Sorry!Company {} was unsubscribed!'.format(self.company.name)
        if self.company.status != MembersOrMembershipBase.STATUSES['ACTIVE']:
            return 'Sorry!Company {} is not active!'.format(self.company.name)
        if not user_right:
            return 'You haven\'t got aproriate rights!'
        return True

    @staticmethod
    def get_avaliable_statuses():
        return PRBase.del_attr_by_keys(MembersOrMembershipBase.STATUSES,
                                       ['DELETED', 'FROZEN'])

class MembersRights(MembersOrMembershipBase):
    ACTIONS_FOR_STATUSES = {
        MembersOrMembershipBase.STATUSES['ACTIVE']: {
            MembersOrMembershipBase.ACTIONS['ALLOW']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
            MembersOrMembershipBase.ACTIONS['REJECT']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
            MembersOrMembershipBase.ACTIONS['SUSPEND']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES}},
        MembersOrMembershipBase.STATUSES['APPLICANT']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
            MembersOrMembershipBase.ACTIONS['ENLIST']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES}},
        MembersOrMembershipBase.STATUSES['SUSPENDED']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
            MembersOrMembershipBase.ACTIONS['RESTORE']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES}},
        MembersOrMembershipBase.STATUSES['FROZEN']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES}},
        MembersOrMembershipBase.STATUSES['REJECTED']: {
            MembersOrMembershipBase.ACTIONS['RESTORE']: {'employee':UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES}},
        MembersOrMembershipBase.STATUSES['DELETED']: {}
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id), status=self.member_company.status)

    def action_is_allowed(self, action_name, employee):
        return self.action_is_allowed_member_company(action_name, employee, {'company members': self.member_company.company})



class MembershipRights(MembersOrMembershipBase):

    ACTIONS_FOR_STATUSES = {
        MembersOrMembershipBase.STATUSES['ACTIVE']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
            MembersOrMembershipBase.ACTIONS['FREEZE']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}},
        MembersOrMembershipBase.STATUSES['APPLICANT']: {
            MembersOrMembershipBase.ACTIONS['WITHDRAW']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}},
        MembersOrMembershipBase.STATUSES['SUSPENDED']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}},
        MembersOrMembershipBase.STATUSES['FROZEN']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
            MembersOrMembershipBase.ACTIONS['RESTORE']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}},
        MembersOrMembershipBase.STATUSES['REJECTED']: {
            MembersOrMembershipBase.ACTIONS['WITHDRAW']: {'employee':UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}},
        MembersOrMembershipBase.STATUSES['DELETED']: {}
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id),
                                                    status=self.member_company.status)

    def action_is_allowed(self, action_name, employee):
        add_check ={}
        if action_name == MembersOrMembershipBase.ACTIONS['FREEZE']:
            add_check = {'membership':self.member_company.portal.own_company}
        return self.action_is_allowed_member_company(action_name, employee, add_check)


# THIS IS CLASSES FOR CHECK APPROPRIATE RULE

#base rights
class UserIsActive(BaseRightsInProfireader):
    def __init__(self, user=None):
        self.user = user if user else g.user

    def is_allowed(self):
        allow = self.user.is_active()
        if allow != True:
            return allow
        return True

class CanCreateCompanyRight(UserIsActive):
    pass


# rights in filemanager

class CanUpload(FilemanagerRights):
    pass

# base rights employee in company

class UserIsEmployee(BaseRightsEmployeeInCompany):
    def is_allowed(self):
        if self.company:
            return True if UserCompany.get(company_id=self.company.id) else False
        if self.material:
            return True if UserCompany.get(company_id=self.material.company.id) else False

class EditCompanyRight(BaseRightsEmployeeInCompany):

    def is_allowed(self):
        return self.is_action_allowed(self.ACTIONS['EDIT_COMPANY'])

class EditPortalRight(BaseRightsEmployeeInCompany):

    def is_allowed(self):
        return self.is_action_allowed(self.ACTIONS['EDIT_PORTAL'])

class RequireMembereeAtPortalsRight(BaseRightsEmployeeInCompany):

    def is_allowed(self):
        return self.is_action_allowed(self.ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS'])

class PortalManageMembersCompaniesRight(BaseRightsEmployeeInCompany):
    def is_allowed(self):
        return self.is_action_allowed(self.ACTIONS['PORTAL_MANAGE_MEMBERS_COMPANIES'])

class EmployeeAllowRight(EmployeesRight):
    def is_allowed(self):
        self.employment = UserCompany.get(user_id=self.user_id, company_id=self.company.id)
        return self.action_is_allowed(self.ACTIONS['ALLOW'])

# rights in work with articles

class EditMaterialRight(EditOrSubmitMaterialInPortal):
    def is_allowed(self):
        return self.action_is_allowed(self.ACTIONS['EDIT'])

class EditPublicationRight(PublishUnpublishInPortal):
    def is_allowed(self):
        self.company = self.publication.company
        self.division = self.publication.division
        return self.actions()[self.ACTIONS['EDIT']]


        #        company_alias1 = aliased(Company)
        #        company_alias2 = aliased(Company)
        #        participants = db(ArticlePortalDivision, company_alias1, MemberCompanyPortal, company_alias2) \
        #            .join(company_alias1, company_alias1.id == ArticlePortalDivision.article_company_id) \
        #            .join(MemberCompanyPortal, MemberCompanyPortal.company_id == company_alias1.id) \
        # \
        #            .filter(ArticlePortalDivision.id == self.id).all()
        #
        #        for parts in participants:
        #            for p in parts:
        #                print(p.get_client_side_dict())
        #                print('____________________next________________________')
        #            print("______________________________END_____________________________")
        #        print('THEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE ENDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD')

class RIGHTS:
    @staticmethod
    def UPLOAD_FILES():
        return 'upload_files'

    @staticmethod
    def SUBMIT_PUBLICATIONS():
        return 'submit_publications'

    @staticmethod
    def ACCEPT_REFUSE_PUBLICATION():
        return 'accept_refuse_publication'

    @staticmethod
    def PUBLISH():
        return 'publish'

    @staticmethod
    def UNPUBLISH():
        return 'un_publish'

    @staticmethod
    def DELETE_FILES():
        return 'delete_files'

    @staticmethod
    def ADD_EMPLOYEE():
        return 'add_employee'

    @staticmethod
    def SUSPEND_EMPLOYEE():
        return 'suspend_employee'

    @staticmethod
    def SUBSCRIBE_TO_PORTALS():
        return 'subscribe_to_portals'

    @staticmethod
    def MANAGE_RIGHTS_COMPANY():
        return 'manage_rights_company'

    @staticmethod
    def EDIT():
        return 'edit'

    @staticmethod
    def MANAGE_PORTAL():
        return 'manage_portal'

    @staticmethod
    def ARTICLE_PRIORITY():
        return 'article_priority'

    @staticmethod
    def MANAGE_READERS():
        return 'manage_readers'

    @staticmethod
    def REMOVE_PUBLICATION():
        return 'remove_publication'

    @staticmethod
    def MANAGE_COMMENTS():
        return 'manage_comments'

    @staticmethod
    def MANAGE_COMPANIES_MEMBERS():
        return 'manage_companies_members'


# read this:
# http://stackoverflow.com/questions/9058305/getting-attributes-of-a-class
def get_my_attributes(my_class, with_values=False):
    attributes = inspect.getmembers(my_class,
                                    lambda a: not(inspect.isroutine(a)))
    if not with_values:
        return [a[0] for a in attributes if
                not(a[0].startswith('__') and a[0].endswith('__'))]
    else:
        return [a for a in attributes if
                not(a[0].startswith('__') and a[0].endswith('__'))]


class RightAtomic(dict):
    UPLOAD_FILES = ('upload_files', 0x00008, "Upload files to company's folder", 1)
    SUBMIT_PUBLICATIONS = ('submit_publications', 0x00080, 'Submit materials to company', 2)
    ACCEPT_REFUSE_PUBLICATION = ('accept_refuse_publication', 0x08000, 'Accept or refuse submitted materials', 3)
    PUBLISH = ('publish', 0x00002, "Publish company's materials to portal", 4)
    UNPUBLISH = ('unpublish', 0x00004, "Unpublish company's publication from portal", 5)
    DELETE_FILES = ('delete_files', 0x00010, "Remove files from company's folder", 6)
    ADD_EMPLOYEE = ('add_employee', 0x00020, 'Approve new employee', 7)
    SUSPEND_EMPLOYEE = ('suspend_employee', 0x00040, 'Suspend and unsuspend employee', 8)
    SUBSCRIBE_TO_PORTALS = ('subscribe_to_portals', 0x04000, 'Apply company request for portal membership', 9)
    MANAGE_RIGHTS_COMPANY = ('manage_rights_company', 0x00100, 'Change rights for company employees', 10)
    EDIT = ('edit', 0x00001, 'Edit company profile', 11)
    MANAGE_PORTAL = ('manage_portal', 0x00200, 'Create portal and manage portal divisions', 12)
    ARTICLE_PRIORITY = ('article_priority', 0x00400, 'Set publication priority on portal', 13)
    MANAGE_READERS = ('manage_readers', 0x0800, 'Manage readers subscriptions', 14)
    REMOVE_PUBLICATION = ('remove_publication', 0x10000, 'Remove any publication from owned portal', 15)
    MANAGE_COMMENTS = ('manage_comments', 0x2000, 'Manages comments', 16)
    MANAGE_COMPANIES_MEMBERS = ('manage_companies_members', 0x01000, 'Accept or refuse company membership on portal', 17)

    # read this:
    # http://stackoverflow.com/questions/9058305/getting-attributes-of-a-class
    @classmethod
    def keys(cls, with_values=False):
        attributes = inspect.getmembers(cls, lambda a: not(inspect.isroutine(a)))
        if not with_values:
            return [a[0] for a in attributes if
                    not(a[0].startswith('__') and a[0].endswith('__'))]
        else:
            return [a for a in attributes if
                    not(a[0].startswith('__') and a[0].endswith('__'))]

    @classmethod
    def __getitem__(cls, attr):
        return getattr(cls, attr.upper())[0]

# list_of_RightAtomic_attributes = get_my_attributes(RightAtomic)


class RightHumnReadible(RightAtomic):
    @classmethod
    def __getitem__(cls, attr):
        return getattr(cls, attr.upper())[2]


class Right(RightAtomic):
    # renamed from RIGHTS

    @classmethod
    def VALUE_RIGHT(cls):
        return {getattr(RightAtomic, field)[1]: getattr(RightAtomic, field)[0]
                for field in RightAtomic.keys()}

    @classmethod
    def RIGHT_VALUE(cls):
        return {getattr(RightAtomic, field)[0]: getattr(RightAtomic, field)[1]
                for field in RightAtomic.keys()}

    @classmethod
    def RIGHT_POSITION(cls):
        return {getattr(RightAtomic, field)[0]: getattr(RightAtomic, field)[3]
                for field in RightAtomic.keys()}

    @classmethod
    def transform_rights_into_set(cls, rights_in_integer):
        rights_in_integer = rights_in_integer & ALL_AVAILABLE_RIGHTS_TRUE
        return \
            frozenset(
                [cls.VALUE_RIGHT()[2**position] for position, right in
                 enumerate(
                     list(map(int, list(bin(rights_in_integer)[2:][::-1])))
                 )
                 if right]
            )

    # TODO (AA to AA): check the correctness!!!
    @classmethod
    def transform_rights_into_integer(cls, rights_iterable):
        rez = reduce(lambda x, y: x | cls.RIGHT_VALUE()[y], rights_iterable, 0)
        return rez

#  we really need RightAtomic to be inherited from dict.
Right = Right()
RightHumnReadible = RightHumnReadible()
# Now Right['edit'] returns 'edit'


# Base rights are added when user becomes confirmed in company
# BASE_RIGHTS_IN_COMPANY = 136
BASE_RIGHTS_IN_COMPANY = \
    Right.UPLOAD_FILES[1] | \
    Right.SUBMIT_PUBLICATIONS[1]

# ALL_AVAILABLE_RIGHTS_TRUE = 32767
ALL_AVAILABLE_RIGHTS_TRUE = \
    reduce(lambda x, y: x | y,
           map(lambda x: x[1][1], get_my_attributes(RightAtomic, True)))

ALL_AVAILABLE_RIGHTS_FALSE = 0
