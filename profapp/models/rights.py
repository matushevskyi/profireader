from functools import reduce
import inspect
from flask import g
from utils.db_utils import db
from ..models.company import Company, UserCompany, MemberCompanyPortal
from ..models.portal import Portal
from ..models.articles import ArticlePortalDivision, ArticleCompany
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

    def check_objects_statuses(self, objects, action_name):
        user_active = self.check_user_status(action_name)
        if user_active != True:
            return user_active
        for key in objects:
            if not objects[key]:
                return "Unconfirmed {}!".format(key)
            if objects[key].status != 'ACTIVE':
                return "{} should be with status `{}` to perform action `{}`".format(key, 'ACTIVE', action_name)
        return True

    def check_user_status(self, action_name):
        if g.user._banned:
            return "User shouldn`d be baned to perform action `{}`".format(action_name)
        if not g.user.tos:
            return "User must confirm license first to perform action `{}`".format(action_name)
        if not g.user.confirmed:
            return "User must confirmed to perform action `{}`".format(action_name)
        return True

    def check_rights(self, action_name, objects_dict_with_rights, objects):
        for object in objects_dict_with_rights:
            if isinstance(objects_dict_with_rights[object], list):
                for right in objects_dict_with_rights[object]:
                    if not objects[object].has_rights(right):
                        return "{} need right `{}` to perform action `{}`".format(object, right, action_name)
            elif not objects[object].has_rights(objects_dict_with_rights[object]):
                return "{} need right `{}` to perform action `{}`".format(object, objects_dict_with_rights[object], action_name)
        return True

    @staticmethod
    def _is_action_allowed(self, action_name, check_objects_status, check_objects_rights, actions=None, actions_for_statuses=None):
        required_rights = None

        if not action_name in actions:
            return "Unrecognized action `{}`".format(action_name)

        if not self.status in actions_for_statuses:
            return "Unrecognized status `{}`".format(self.status)

        if not action_name in actions_for_statuses[self.status]:
            return "Action `{}` is not applicable for publication with status `{}`".format(action_name,
                                                                                           self.status)
        check_status_in_objects = BaseRightsInProfireader().check_objects_statuses(check_objects_status, action_name)
        if check_status_in_objects != True:
            return check_status_in_objects

        if self.status in actions_for_statuses:
            required_rights = actions_for_statuses[self.status][action_name]

        result = BaseRightsInProfireader().check_rights(action_name, required_rights, check_objects_rights)
        if result != True:
            return result

        return True

    @staticmethod
    def base_actions(self, *args, status=None):
        print(status)
        return {action_name: self.action_is_allowed(action_name, *args) for action_name
                in self.ACTIONS_FOR_STATUSES[status]}


class PublishUnpublishInPortal(BaseRightsInProfireader):

        def __init__(self, publication, portal, company):
            self.publication = publication if isinstance(publication, ArticlePortalDivision) else ArticlePortalDivision.get(publication)
            self.portal = portal if isinstance(portal, Portal) else Portal.get(portal)
            self.company = company if isinstance(company, Company) else Company.get(Company)

        STATUSES = {'SUBMITTED': 'SUBMITTED', 'UNPUBLISHED': 'UNPUBLISHED', 'PUBLISHED': 'PUBLISHED',
                    'DELETED': 'DELETED'}
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
            return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id),
                    MemberCompanyPortal.get(portal_id=self.publication.division.portal_id, company_id=self.company.id),
                                                        self.portal.own_company, status=self.publication.status)

        def action_is_allowed(self, action_name, employee, membership, company_object):
            check_objects_status = {'employeer':self.company,
                                    'employee': employee,
                                    'membership': membership,
                                    'company where you want update publication': company_object}

            return BaseRightsInProfireader._is_action_allowed(self.publication, action_name,
                        check_objects_status, {'employment': employee, 'membership': membership},
                        actions=self.ACTIONS, actions_for_statuses=self.ACTIONS_FOR_STATUSES)

class EditOrSubmitMaterialInPortal(BaseRightsInProfireader):

    def __init__(self, material, portal):
        self.material = material if isinstance(material, ArticleCompany) else ArticleCompany.get(material)
        self.portal = portal if isinstance(portal, Portal) else Portal.get(portal)

    ACTIONS = {
        'SUBMIT': 'SUBMIT',
        'EDIT': 'EDIT'
    }
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    ACTIONS_FOR_STATUSES = {
        STATUSES['NORMAL']: {
            ACTIONS['SUBMIT']: {'employment': UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH ,
                                'membership': MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH},
            ACTIONS['EDIT']: {'employment': UserCompany.RIGHT_AT_COMPANY.ARTICLES_EDIT_OTHERS or UserCompany.RIGHT_AT_COMPANY._OWNER}
        }
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.material.company.id),
                                                    MemberCompanyPortal.get(portal_id=self.portal.id,
                                                                            company_id=self.material.company.id),
                                                    self.portal.own_company, status=self.material.status)

    def action_is_allowed(self, action_name, employee, membership, company_object):
        check_objects_status = {'company owner material': self.material.company,
                                'employee': employee, 'membership': membership,
                                'company where you want submit material': company_object}

        return BaseRightsInProfireader._is_action_allowed(self.material, action_name,
                check_objects_status,{'company owner material': self.material.company,'employment': employee, 'membership': membership},
                            actions=self.ACTIONS, actions_for_statuses=self.ACTIONS_FOR_STATUSES)

class BaseRightsEmployeeInCompany(BaseRightsInProfireader):
    def __init__(self, company=None, employment=None, member_company=None):
        self.company = company if isinstance(company, Company) else Company.get(company)
        self.employment = employment
        self.member_company = member_company

    ACTIONS = {
        'EDIT_COMPANY': 'EDIT_COMPANY',
        'EDIT_PORTAL': 'EDIT_PORTAL',
        'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS':'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS'
    }

    ACTIONS_FOR_EMPLOYEE_IN_COMPANY = {
        'ACTIVE': {
            ACTIONS['EDIT_COMPANY']: {'employee': UserCompany.RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE},
            ACTIONS['EDIT_PORTAL']: {'employee': UserCompany.RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE},
            ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS']: {'employee': UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS}
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

    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE', 'FIRED': 'FIRED'}

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

    def action_is_allowed(self, action_name, employee):
        if action_name == 'FIRE':
                if self.employment.user_id == employee.employer.author_user_id:
                    return 'You can`t fire company owner'

        if action_name == 'ALLOW':
                if self.employment.user_id == employee.employer.author_user_id:
                    return 'Company owner have all permissions and you can do nothing with that'
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company}
        return BaseRightsInProfireader._is_action_allowed(self.employment, action_name,
                get_objects_for_check, {'employee': employee},actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id), status=self.employment.status)


class EditCompanyRight(BaseRightsEmployeeInCompany):

    def is_edit_allowed(self):
        return self.is_action_allowed(self.ACTIONS['EDIT_COMPANY'])

class EditPortalRight(BaseRightsEmployeeInCompany):

    def is_edit_allowed(self):
        return self.is_action_allowed(self.ACTIONS['EDIT_PORTAL'])

class RequireMembereeAtPortalsRight(BaseRightsEmployeeInCompany):

    def is_require_member_allowed(self):
        return self.is_action_allowed(self.ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS'])


class MembersOrMembershipBase(BaseRightsEmployeeInCompany):
    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE',
                'SUSPENDED': 'SUSPENDED', 'FROZEN': 'FROZEN', 'DELETED': 'DELETED'}
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
