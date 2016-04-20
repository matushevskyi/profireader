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
    def is_action_for_article_allowed(self, action_name, employment, membership, check_objects, actions, actions_for_statuses):
        required_rights = None
        if not employment:
            return "Unconfirmed employment"

        if not membership:
            return "Unconfirmed membership"

        if not action_name in actions:
            return "Unrecognized action `{}`".format(action_name)

        if not self.status in actions_for_statuses:
            return "Unrecognized status `{}`".format(self.status)

        if not action_name in actions_for_statuses[self.status]:
            return "Action `{}` is not applicable for publication with status `{}`".format(action_name,
                                                                                           self.status)

        check_status_in_objects = BaseRightsInProfireader().check_objects_statuses(check_objects, action_name)
        if check_status_in_objects != True:
            return check_status_in_objects

        if self.status in actions_for_statuses:
            required_rights = actions_for_statuses[self.status][action_name]

        result = BaseRightsInProfireader().check_rights(action_name, required_rights,
                                   {'employment': employment, 'membership': membership})
        if result != True:
            return result

        return True

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
            employment = UserCompany.get(company_id=self.company.id)
            membership = MemberCompanyPortal.get(portal_id=self.publication.division.portal_id, company_id=self.company.id)
            company_object = self.portal.own_company
            return {action_name: self.action_is_allowed(action_name, employment, membership, company_object) for action_name in
                    self.ACTIONS_FOR_STATUSES[self.publication.status]}

        def action_is_allowed(self, action_name, employment, membership, company_object):
            get_objects_for_check = {'employment': employment,
                                        'membership': membership,
                                        'company where you want update publication': company_object}

            return BaseRightsInProfireader.is_action_for_article_allowed(self.publication, action_name,
                                                      employment, membership, get_objects_for_check, self.ACTIONS, self.ACTIONS_FOR_STATUSES)

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
        employment = UserCompany.get(company_id=self.material.company.id)
        membership = MemberCompanyPortal.get(portal_id=self.portal.id, company_id=self.material.company.id)
        company_object = self.portal.own_company
        return {action_name: self.action_is_allowed(action_name, employment, membership, company_object) for action_name in
                self.ACTIONS_FOR_STATUSES[self.material.status]}

    def action_is_allowed(self, action_name, employment, membership, company_object):
        get_objects_for_check = {'company owner material': self.material.company,
                         'employment': employment, 'membership': membership,
                         'company where you want submit material': company_object}

        return BaseRightsInProfireader.is_action_for_article_allowed(self.material, action_name,
                                                     employment, membership, get_objects_for_check, self.ACTIONS,
                                                     self.ACTIONS_FOR_STATUSES)

class RightsEmployeeInCompany(BaseRightsInProfireader):
    def __init__(self, company, employment=None, membership=None, member=None):
        self.company = company if isinstance(company, Company) else Company.get(company)
        self.employment = employment
        self.membership = membership
        self.member = member

    @staticmethod
    def is_action_for_employee_in_company_allowed(check_objects, action_name, employee, require_rights):
        check_status_in_objects = BaseRightsInProfireader().check_objects_statuses(check_objects, action_name)
        if check_status_in_objects != True:
            return check_status_in_objects
        result = BaseRightsInProfireader().check_rights(action_name, require_rights, {'employee': employee})
        if result != True:
            return result
        return True

class FilemanagerRights(RightsEmployeeInCompany):

    ACTIONS = {
        'download': 'download',
        'remove': 'remove',
        'show': 'show',
        'upload': 'upload',
        'cut': 'cut',
        'create_folder': 'create_folder'
    }
    ACTIONS_FOR_FILEMANAGER = {
        'download': UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE,
        'remove': UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS,
        'show': UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE,
        'upload': UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD,
        'cut': UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS,
        'create_folder': UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD
    }

    def is_action_allowed(self, action):
        user_company = UserCompany.get(company_id=self.company.id)
        if user_company:
            result = EmployeesRight.is_action_for_employee_in_company_allowed({'company': self.company},action, user_company,
                 {'employee': [FilemanagerRights.ACTIONS_FOR_FILEMANAGER[action]]})
            if result != True:
                return result
        elif not user_company and action != FilemanagerRights.ACTIONS['show']:
            return "You cannot menage files in joined company!"
        return True



class EmployeesRight(RightsEmployeeInCompany):

    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE', 'FIRED': 'FIRED'}

    ACTIONS = {
        'ENLIST': 'ENLIST',
        'REJECT': 'REJECT',
        'FIRE': 'FIRE',
        'ALLOW': 'ALLOW'
    }

    ACTIONS_FOR_STATUSES = {
        STATUSES['APPLICANT']: {
            ACTIONS['ENLIST']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
            ACTIONS['REJECT']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },
        STATUSES['REJECTED']: {
            ACTIONS['ENLIST']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },

        STATUSES['FIRED']: {
            ACTIONS['ENLIST']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
        },
        STATUSES['ACTIVE']: {
            ACTIONS['FIRE']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]},
            ACTIONS['ALLOW']: {'employment': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS]},
        }
    }

    def action_is_allowed(self, action_name, employee):
        if not employee:
            return "Unconfirmed employment"

        if not action_name in self.ACTIONS:
            return "Unrecognized employee action `{}`".format(action_name)

        if not self.employment.status in self.ACTIONS_FOR_STATUSES:
            return "Unrecognized employee status `{}`".format(self.employment.status)

        if not action_name in self.ACTIONS_FOR_STATUSES[self.employment.status]:
            return "Action `{}` is not applicable for employee with status `{}`".format(action_name,
                                                                                        self.employment.status)

        if employee.status != UserCompany.STATUSES['ACTIVE']:
            return "User need employment with status `{}` to perform action `{}`".format(
                UserCompany.STATUSES['ACTIVE'], action_name)

        if action_name == 'FIRE':
            if self.employment.user_id == employee.employer.author_user_id:
                return 'You can`t fire company owner'

        if action_name == 'ALLOW':
            if self.employment.user_id == employee.employer.author_user_id:
                return 'Company owner have all permissions and you can do nothing with that'

        required_rights = self.ACTIONS_FOR_STATUSES[self.employment.status][action_name]

        if 'employment' in required_rights:
            for required_right in required_rights['employment']:
                if not employee.has_rights(required_right):
                    return "Employment need right `{}` to perform action `{}`".format(required_right, action_name)

        return True

    def actions(self):
        employee = UserCompany.get(company_id=self.company.id)
        return {action_name: self.action_is_allowed(action_name, employee) for action_name in
                self.ACTIONS_FOR_STATUSES[self.employment.status]}


class EditCompanyRight(RightsEmployeeInCompany):
    def is_edit_allowed(self):
        result = EmployeesRight.is_action_for_employee_in_company_allowed({'company': self.company},
                'edit_company_profile',UserCompany.get(company_id=self.company.id),
                                {'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE]})
        return True if result == True else False

class RequireMembereeAtPortalsRight(RightsEmployeeInCompany):
        def is_require_member_allowed(self):
            result = EmployeesRight.is_action_for_employee_in_company_allowed({'company': self.company},
                    'require_member',UserCompany.get(company_id=self.company.id),
                           {'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]})
            return True if result == True else False

class EployeeMembersRights(RightsEmployeeInCompany):

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

    ACTION_FOR_STATUSES_MEMBERSHIP = {
        STATUSES['ACTIVE']: {
            ACTIONS['UNSUBSCRIBE']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS,
            ACTIONS['FREEZE']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
        STATUSES['APPLICANT']: {
            ACTIONS['WITHDRAW']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
        STATUSES['SUSPENDED']: {
            ACTIONS['UNSUBSCRIBE']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
        STATUSES['FROZEN']: {
            ACTIONS['UNSUBSCRIBE']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS,
            ACTIONS['RESTORE']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
        STATUSES['REJECTED']: {
            ACTIONS['WITHDRAW']: UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS},
        STATUSES['DELETED']: {}
    }

    ACTION_FOR_STATUSES_MEMBER = {
        STATUSES['ACTIVE']: {
            ACTIONS['ALLOW']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES,
            ACTIONS['REJECT']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES,
            ACTIONS['SUSPEND']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
        STATUSES['APPLICANT']: {
            ACTIONS['REJECT']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES,
            ACTIONS['ENLIST']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
        STATUSES['SUSPENDED']: {
            ACTIONS['REJECT']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES,
            ACTIONS['RESTORE']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
        STATUSES['FROZEN']: {
            ACTIONS['REJECT']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
        STATUSES['REJECTED']: {
            ACTIONS['RESTORE']: UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES},
        STATUSES['DELETED']: {}
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

    def actions(self, who):
        employee = UserCompany.get(company_id=self.company.id)
        action_for_status = EployeeMembersRights.ACTION_FOR_STATUSES_MEMBER if who == 'member' else EployeeMembersRights.ACTION_FOR_STATUSES_MEMBERSHIP
        return {action_name: self.action_is_allowed(action_name, employee,
                                                    action_for_status[self.membership.status]) for action_name in
                action_for_status[self.membership.status]}

    def action_is_allowed(self, action_name, employee, actions):
        if not employee:
            return "Unconfirmed employment"

        if not action_name in actions:
            return "Unrecognized action `{}`".format(action_name)

        if employee.status != EployeeMembersRights.STATUSES['ACTIVE']:
            return "User need employment with status `{}` to perform action `{}`".format(
                EployeeMembersRights.STATUSES['ACTIVE'], action_name)

        if self.membership.portal.own_company.status != 'ACTIVE' and action_name == EployeeMembersRights.ACTIONS['FREEZE']:
            return "Company `{}` with status `{}` need status ACTIVE to perform action `{}`".format(
                self.membership.portal.own_company.name,
                self.membership.portal.own_company.status, action_name)
        if self.membership.portal.company_owner_id == self.membership.company_id:
            return 'You can`t {0} portal of your own company'.format(action_name)

        if not employee.has_rights(actions[action_name]):
            return "Employment need right `{}` to perform action `{}`".format(actions[action_name], action_name)

        return True

    def can_update_company_partner(self):
        user_right = UserCompany.get(company_id=self.company.id).has_rights(UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES)
        if self.membership.status == EployeeMembersRights.STATUSES['FROZEN'] and not user_right:
            return 'Sorry!You can not manage company {}!It was frozen!'.format(self.company.name)
        if self.membership.status == EployeeMembersRights.STATUSES['DELETED']:
            return 'Sorry!Company {} was unsubscribed!'.format(self.company.name)
        if self.company.status != EployeeMembersRights.STATUSES['ACTIVE']:
            return 'Sorry!Company {} is not active!'.format(self.company.name)
        if not user_right:
            return 'You haven\'t got aproriate rights!'
        return True

    @staticmethod
    def get_avaliable_statuses():
        return PRBase.del_attr_by_keys(EployeeMembersRights.STATUSES,
                                       ['DELETED', 'FROZEN'])





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
