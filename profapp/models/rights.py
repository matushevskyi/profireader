from functools import reduce
import inspect
from flask import g
from utils.db_utils import db
from ..models.company import Company, UserCompany, MemberCompanyPortal
from ..models.portal import Portal, PortalDivision
# from ..models.bak_articles import ArticlePortalDivision, ArticleCompany
from ..models.materials import Material, Publication
from ..models.users import User
from .pr_base import PRBase
import re


# COMPANY_OWNER = ['edit', 'publish', 'unpublish', 'upload_files', 'delete_files', 'add_employee',
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
    ACTIONS = {
        'CREATE_COMPANY': 'CREATE_COMPANY',
        'EDIT_USER_PROFILE': 'EDIT_USER_PROFILE',
        'SUBSCRIBE_TO_PORTAL': 'SUBSCRIBE_TO_PORTAL'
    }

    def __setattr__(self, key, value):
        key, value = self.get_allowed_attributes(key, value)
        object.__setattr__(self, key, value)

    def get_allowed_attributes(self, key, value):
        return key, value

    def check_objects_statuses(self, objects, action_name):
        user_active = g.user.is_active()
        if user_active != True:
            return user_active
        for key in objects:
            if not objects[key]:
                return "Non existent {}!".format(key)
            if objects[key].is_active() != True:
                return "{} should be active to perform action `{}`".format(key, action_name)
        return True

    def check_rights(self, action_name, necessary_rights, objects_for_check):

        if isinstance(necessary_rights, tuple):
            _any = []
            allow = True
            for dict_rights in necessary_rights:
                allow = self.rights_allowed(action_name, dict_rights, objects_for_check)
                _any.append(True) if allow == True else _any.append(False)

            return True if any(_any) else allow
        else:
            return self.rights_allowed(action_name, necessary_rights, objects_for_check)

    def rights_allowed(self, action_name, rights, objects_for_check):
        allow = True
        for object in rights:
            if not object in rights:
                raise Exception('Rights object doesn`t containts {}'.format(object))
            if not object in objects_for_check:
                raise Exception('Objects for check rights doesn`t containts {}'.format(object))
            if isinstance(rights[object], list):
                for right in rights[object]:
                    if isinstance(right, str):
                        if objects_for_check[object].has_rights(right) != True:
                            allow = "{} need right `{}` to perform action `{}`".format(object, right,
                                                                                       action_name)
                    if callable(right):
                        allow = right(objects_for_check)
            elif isinstance(rights[object], tuple):
                allow = self._any(object, rights[object], objects_for_check, action_name)
            elif callable(rights[object]):
                allow = rights[object](objects_for_check)
            else:
                raise Exception('Wrong data type!')
            if allow != True:
                return allow
        return True

    def _any(self, object, rights, objects_for_check, action_name):
        allow = True
        _any = []
        for right in rights:
            if isinstance(right, str):
                if objects_for_check[object].has_rights(right) != True:
                    _any.append(False)
                    allow = "{} need right `{}` to perform action `{}`".format(object, right,
                                                                               action_name)
                else:
                    _any.append(True)
            if callable(right):
                allow = right(objects_for_check)
                if allow != True:
                    _any.append(False)
                else:
                    _any.append(True)
        if any(_any):
            return True
        else:
            return allow

    @staticmethod
    def _is_action_allowed(self, action_name, objects_for_check_status, objects_for_check_rights=None, actions=None,
                           actions_for_statuses=None):
        required_rights = None
        if not action_name.upper() in actions.keys():
            return "Unrecognized action `{}`".format(action_name)
        if actions_for_statuses:
            if not self.status in actions_for_statuses:
                return "Unrecognized status `{}`".format(self.status)
            if not action_name in actions_for_statuses[self.status].keys():
                return "Action `{}` is not applicable with status `{}`".format(action_name, self.status)
            if self.status in actions_for_statuses:
                required_rights = actions_for_statuses[self.status][action_name]

        check_status_in_objects = BaseRightsInProfireader().check_objects_statuses(objects_for_check_status,
                                                                                   action_name)
        if check_status_in_objects != True:
            return check_status_in_objects

        result = BaseRightsInProfireader().check_rights(action_name, required_rights,
                                                        objects_for_check_rights) if required_rights else True

        return result if result != True else True

    @staticmethod
    def base_actions(self, *args, object=None, **kwargs):
        if not isinstance(object, str) and not hasattr(object, 'status'):
            raise Exception('Bad data!')
        return {action_name: self.action_is_allowed(action_name, *args, **kwargs) for action_name
                in self.ACTIONS_FOR_STATUSES[object.status if not isinstance(object, str) else object]}


class PublishUnpublishInPortal(BaseRightsInProfireader):
    def __init__(self, publication=None, division=None, company=None):
        self.publication = publication if isinstance(publication, Publication) else Publication.get(
            publication) if publication else None
        self.division = division if isinstance(division, PortalDivision) else PortalDivision.get(
            division) if division else None
        self.company = company if isinstance(company, Company) else Company.get(company) if company else None

    def get_allowed_attributes(self, key, value):
        if key == 'publication_id':
            key = 'publication'
            value = Publication.get(value)
        elif key == 'company_id':
            key = 'company'
            value = Company.get(value)
        return key, value

    STATUSES = Publication.STATUSES

    ACTIONS = {
        'PUBLISH': 'PUBLISH',
        'UNPUBLISH': 'UNPUBLISH',
        'EDIT': 'EDIT',
        'REPUBLISH': 'REPUBLISH',
        'DELETE': 'DELETE',
        'UNDELETE': 'UNDELETE'
    }

    delete_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH],
                     'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_DELETE]}

    publish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH],
                      'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_DELETE]}

    unpublish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH],
                        'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH]}

    republish_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH,
                                       MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_UNPUBLISH],
                        'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_UNPUBLISH,
                                       UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH]}

    edit_rights = {'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH],
                   'employment': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH]}

    ACTIONS_FOR_STATUSES = {
        STATUSES['SUBMITTED']: {
            ACTIONS['PUBLISH']: publish_rights,
            ACTIONS['DELETE']: delete_rights,
            ACTIONS['EDIT']: edit_rights,
        },
        STATUSES['PUBLISHED']: {
            ACTIONS['REPUBLISH']: republish_rights,
            ACTIONS['UNPUBLISH']: unpublish_rights,
            ACTIONS['EDIT']: edit_rights,
            ACTIONS['DELETE']: delete_rights
        },
        STATUSES['UNPUBLISHED']: {
            ACTIONS['REPUBLISH']: publish_rights,
            ACTIONS['EDIT']: edit_rights,
            ACTIONS['DELETE']: delete_rights
        },
        STATUSES['DELETED']: {
            ACTIONS['UNDELETE']: delete_rights,
        }
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, object=self.publication)

    def action_is_allowed(self, action_name):
        company = self.company if self.company else self.division.portal.own_company \
            if self.division else self.publication.company if self.publication else None
        membership_portal_id = self.division.portal.id if self.division else ''
        if not company:
            raise Exception('Bad data!')
        employee = UserCompany.get(company_id=company.id)
        if not employee:
            return "Sorry!You are not employee in this company!"

        membership = MemberCompanyPortal.get_by_portal_id_company_id(portal_id=membership_portal_id, company_id=company.id)
        if not membership:
            raise Exception('Bad data!')
        company_object = self.division.portal.own_company
        check_objects_status = {'employeer': company,
                                'employee': employee,
                                'membership': membership,
                                'company where you want update publication': company_object,
                                'division': self.division}

        return BaseRightsInProfireader._is_action_allowed(self.publication, action_name,
                                                          check_objects_status,
                                                          {'employment': employee, 'membership': membership},
                                                          actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    def get_active_division(self, divisions):
        return [division.get_client_side_dict() for division in divisions
                if (division.portal_division_type_id in ['events', 'news'] and division.is_active())]

    @staticmethod
    def get_portals_where_company_is_member(company):
        """This method return all portals-partners current company"""
        return [memcomport.portal for memcomport in db(MemberCompanyPortal, company_id=company.id).all()]


class EditOrSubmitMaterialInPortal(BaseRightsInProfireader):
    def __init__(self, material=None, portal=None, division=None):
        self.material = material if isinstance(material, Material) else Material.get(
            material) if material else None
        self.portal = portal if isinstance(portal, Portal) else Portal.get(portal) if portal else None
        self.division = division if isinstance(division, PortalDivision) else PortalDivision.get(
            division) if division else None

    def get_allowed_attributes(self, key, value):
        if key == 'material_id':
            key = 'material'
            value = Material.get(value)
        return key, value

    ACTIONS = {
        'SUBMIT': 'SUBMIT',
        'EDIT': 'EDIT'
    }
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    ACTIONS_FOR_STATUSES = {
        STATUSES['NORMAL']: {
            ACTIONS['SUBMIT']:
                {'employee': [UserCompany.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH],
                 'membership': [MemberCompanyPortal.RIGHT_AT_PORTAL.PUBLICATION_PUBLISH]},
            ACTIONS['EDIT']:
                {'employee': (lambda kwargs: kwargs['material'].editor_user_id == kwargs['user'].id,
                              UserCompany.RIGHT_AT_COMPANY.ARTICLES_EDIT_OTHERS)}
        }
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, object=self.material)

    def action_is_allowed(self, action_name):
        if not self.material:
            raise Exception('Bad data!')
        self.employee = UserCompany.get(company_id=self.material.company.id)
        if not self.employee:
            return "Sorry!You are not employee in this company!"
        check_objects_status = {'company owner material': self.material.company,
                                'employee': self.employee}

        check_objects_status.update({'division': self.division}) if self.division else None

        check_objects_rights = {'company owner material': self.material.company,
                                'employee': self.employee, 'material': self.material, 'user': g.user}
        if self.portal:
            check_objects_rights.update(
                {'membership': MemberCompanyPortal.get_by_portal_id_company_id(portal_id=self.portal.id, company_id=self.material.company.id)})
            check_objects_status.update({'membership': MemberCompanyPortal.get_by_portal_id_company_id(portal_id=self.portal.id,
                                                                               company_id=self.material.company.id),
                                         'company where you want submit material': self.portal.own_company})

        return BaseRightsInProfireader._is_action_allowed(self.material, action_name,
                                                          check_objects_status, check_objects_rights,
                                                          actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)


class BaseRightsEmployeeInCompany(BaseRightsInProfireader):
    def __init__(self, company=None):
        self.company = company if isinstance(company, Company) else Company.get(company) if company else None

    def get_allowed_attributes(self, key, value):
        if key == 'company_id':
            key = 'company'
            value = Company.get(value)
        if key == 'material_id':
            key = 'material'
            value = Material.get(value)
        return key, value

    ACTIONS = {
        'EDIT_COMPANY': 'EDIT_COMPANY',
        'EDIT_PORTAL': 'EDIT_PORTAL',
        'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS': 'COMPANY_REQUIRE_MEMBEREE_AT_PORTALS',
        'PORTAL_MANAGE_MEMBERS_COMPANIES': 'PORTAL_MANAGE_MEMBERS_COMPANIES',
        'EMPLOYEE_ALLOW_RIGHTS': 'EMPLOYEE_ALLOW_RIGHTS',
        'CREATE_MATERIAL': 'CREATE_MATERIAL'
    }

    ACTIONS_FOR_EMPLOYEE_IN_COMPANY = {
        'ACTIVE': {
            ACTIONS['EDIT_COMPANY']: {'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_EDIT_PROFILE]},
            ACTIONS['EDIT_PORTAL']: {'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_EDIT_PROFILE]},
            ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]},
            ACTIONS['PORTAL_MANAGE_MEMBERS_COMPANIES']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]},
            ACTIONS['EMPLOYEE_ALLOW_RIGHTS']: {'employee': [UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS]},
            ACTIONS['CREATE_MATERIAL']: {},
        }
    }

    def action_is_allowed(self, action):
        if not self.company:
            raise Exception('Bad data')
        employee = UserCompany.get(company_id=self.company.id)
        if not employee:
            return "Sorry!You are not employee in this company!"
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company}
        return BaseRightsInProfireader._is_action_allowed(employee, action,
                                                          get_objects_for_check, {'employee': employee},
                                                          actions=BaseRightsEmployeeInCompany.ACTIONS,
                                                          actions_for_statuses=BaseRightsEmployeeInCompany.ACTIONS_FOR_EMPLOYEE_IN_COMPANY)


class FilemanagerRights(BaseRightsEmployeeInCompany):
    def __init__(self, company=None):
        super(FilemanagerRights, self).__init__(company=company)
        self.employee = UserCompany.get(company_id=self.company.id)

    ACTIONS = {
        'DOWNLOAD': 'download',
        'REMOVE': 'remove',
        'SHOW': 'show',
        'UPLOAD': 'upload',
        'CUT': 'cut',
        'CREATE_FOLDER': 'create_folder',
        'PROPERTIES': 'properties',
        'PASTE': 'paste',
        'COPY': 'copy',
        'CHOOSE': 'choose'
    }

    ACTIONS_FOR_STATUSES = {
        'ACTIVE': {
            ACTIONS['PROPERTIES']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD],
                                    'file': lambda kwargs: None if kwargs['file'].mime == "root" else True},
            ACTIONS['PASTE']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD],
                               'file': lambda kwargs: None if kwargs['file'] == None else True},
            ACTIONS['COPY']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE],
                              'file': lambda kwargs: None if kwargs['file'].mime == "root" else True},
            ACTIONS['REMOVE']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS],
                                'file': lambda kwargs: None if kwargs['file'].mime == "root" else True},
            ACTIONS['CUT']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_DELETE_OTHERS],
                             'file': lambda kwargs: None if kwargs['file'].mime == "root" else True},
        },
        'NONE': {
            ACTIONS['PROPERTIES']: {'employee': lambda kwargs: False},
            ACTIONS['PASTE']: {'employee': lambda kwargs: False},
            ACTIONS['COPY']: {'employee': lambda kwargs: True},
            ACTIONS['REMOVE']: {'employee': lambda kwargs: False},
            ACTIONS['CUT']: {'employee': lambda kwargs: False}
        }

    }

    ACTIONS_FOR_FILEMANAGER = {
        'ACTIVE': {
            ACTIONS['SHOW']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_BROWSE]},
            ACTIONS['UPLOAD']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD]},
            ACTIONS['CREATE_FOLDER']: {'employee': [UserCompany.RIGHT_AT_COMPANY.FILES_UPLOAD]}
        }
    }

    def actions(self, file, called_for):
        if not file:
            raise Exception('Bad data!')
        actions = BaseRightsInProfireader.base_actions(self, file, object=self.employee if self.employee else 'NONE')
        default_actions = {}
        default_actions['download'] = None if ((file.mime == 'directory') or (file.mime == 'root')) else True
        if called_for == 'file_browse_image':
            default_actions['choose'] = False if None == re.search('^image/.*', file.mime) else True
            actions['choose'] = False if None == re.search('^image/.*', file.mime) else True.bit_length()
        elif called_for == 'file_browse_media':
            default_actions['choose'] = False if None == re.search('^video/.*', file.mime) else True
            actions['choose'] = False if None == re.search('^video/.*', file.mime) else True
        elif called_for == 'file_browse_file':
            default_actions['choose'] = True
            actions['choose'] = True
        actions.update({act: default_actions[act] for act in default_actions})
        return actions

    def action_is_allowed(self, action, file=None):

        if self.employee:
            objects_for_check_status = {'employee': self.employee,
                                        'employeer': self.company}
            objects_for_check_rights = {'employee': self.employee}
            if file:
                objects_for_check_rights.update({'file': file})
                action_for_status = FilemanagerRights.ACTIONS_FOR_STATUSES
            else:
                action_for_status = FilemanagerRights.ACTIONS_FOR_FILEMANAGER
            result = BaseRightsInProfireader._is_action_allowed(self.employee, action, objects_for_check_status,
                                                                objects_for_check_rights,
                                                                actions=FilemanagerRights.ACTIONS,
                                                                actions_for_statuses=action_for_status)
            if result != True:
                return result
        elif not self.employee and action != FilemanagerRights.ACTIONS['SHOW'] and action != FilemanagerRights.ACTIONS[
            'COPY']:
            return "You cannot menage files in joined company!"
        return True


class EmployeesRight(BaseRightsEmployeeInCompany):
    def __init__(self, company=None, employment=None):
        super(EmployeesRight, self).__init__(company=company)
        self.employment = employment if isinstance(employment, UserCompany) else \
            UserCompany.get(user_id=employment, company_id=self.company.id) if employment and company else None

    def get_allowed_attributes(self, key, value):
        if key == 'user_id':
            key = 'user'
            value = User.get(value)
        if key == 'company_id':
            key = 'company'
            value = Company.get(value)
        if key == 'employment_id':
            key = 'employment'
            value = db(UserCompany, id=value).first()
        return key, value

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
            ACTIONS['FIRE']:
                {'employee': [lambda kwargs: 'You can`t fire company owner'
                if kwargs['employment'].user_id == kwargs['employee'].company.author_user_id else True,
                              UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]
                 },
            ACTIONS['ALLOW']:
                {'employee': [lambda kwargs: 'Company owner have all permissions and you can do nothing with that'
                if kwargs['employment'].user_id == kwargs['employee'].company.author_user_id else True,
                              UserCompany.RIGHT_AT_COMPANY.EMPLOYEE_ALLOW_RIGHTS]},
        }
    }

    def action_is_allowed(self, action_name):
        if not self.company:
            raise Exception('Bad data!')
        if not self.employment:
            raise Exception('Bad data!')
        employee = UserCompany.get(company_id=self.company.id)
        if not employee:
            return "Sorry!You are not employee in this company!"
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company,
                                 'user': self.employment.user}
        return BaseRightsInProfireader._is_action_allowed(self.employment, action_name,
                                                          get_objects_for_check,
                                                          {'employee': employee, 'employment': self.employment},
                                                          actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, object=self.employment)


class MembersOrMembershipBase(BaseRightsInProfireader):
    def __init__(self, company=None, member_company=None):
        self.company = company if isinstance(company, Company) else Company.get(company) if company else None
        self.member_company = member_company

    STATUSES = MemberCompanyPortal.STATUSES
    INITIALLY_FILTERED_OUT_STATUSES = [STATUSES['DELETED'], STATUSES['REJECTED']]
    MEMBER = 'member'
    MEMBERSHIP = 'membership'

    def get_allowed_attributes(self, key, value):
        return key, value

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
        get_objects_for_check = {'employee': employee,
                                 'employeer': self.company}
        if add_to_check_statuses:
            get_objects_for_check.update(add_to_check_statuses)
        return BaseRightsInProfireader._is_action_allowed(self.member_company, action_name,
                                                          get_objects_for_check,
                                                          {'employee': employee, 'member': self.member_company},
                                                          actions=self.ACTIONS,
                                                          actions_for_statuses=self.ACTIONS_FOR_STATUSES)

    @staticmethod
    def get_avaliable_statuses():
        return PRBase.del_attr_by_keys(MembersOrMembershipBase.STATUSES,
                                       ['DELETED', 'FROZEN'])


class MembersRights(MembersOrMembershipBase):
    ACTIONS_FOR_STATUSES = {
        MembersOrMembershipBase.STATUSES['ACTIVE']: {
            MembersOrMembershipBase.ACTIONS['ALLOW']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES],
                'member': lambda kwargs: 'You can`t allow portal of your own company!' if
                kwargs['member'].portal.company_owner_id == kwargs['member'].company_id else True},
            MembersOrMembershipBase.ACTIONS['REJECT']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES],
                'member': lambda kwargs: 'You can`t reject portal of your own company!' if
                kwargs['member'].portal.company_owner_id == kwargs['member'].company_id else True},
            MembersOrMembershipBase.ACTIONS['SUSPEND']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES],
                'member': lambda kwargs: 'You can`t suspend portal of your own company!' if
                kwargs['member'].portal.company_owner_id == kwargs['member'].company_id else True}},
        MembersOrMembershipBase.STATUSES['APPLICANT']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]},
            MembersOrMembershipBase.ACTIONS['ENLIST']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]}},
        MembersOrMembershipBase.STATUSES['SUSPENDED']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]},
            MembersOrMembershipBase.ACTIONS['RESTORE']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]}},
        MembersOrMembershipBase.STATUSES['FROZEN']: {
            MembersOrMembershipBase.ACTIONS['REJECT']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]}},
        MembersOrMembershipBase.STATUSES['REJECTED']: {
            MembersOrMembershipBase.ACTIONS['RESTORE']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES]}},
        MembersOrMembershipBase.STATUSES['DELETED']: {}
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id),
                                                    object=self.member_company)

    def action_is_allowed(self, action_name, employee):
        add_check = {'company members': self.member_company.company} if action_name != MembersOrMembershipBase.ACTIONS[
            'REJECT'] else {}
        return self.action_is_allowed_member_company(action_name, employee, add_check)


class MembershipRights(MembersOrMembershipBase):
    ACTIONS_FOR_STATUSES = {
        MembersOrMembershipBase.STATUSES['ACTIVE']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']:
                {'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS],
                 'member': lambda kwargs: 'You can`t unsubscribe portal of your own company!' if
                 kwargs['member'].portal.company_owner_id == kwargs['member'].company_id else True},
            MembersOrMembershipBase.ACTIONS['FREEZE']:
                {'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS],
                 'member': lambda kwargs: 'You can`t freeze portal of your own company!' if
                 kwargs['member'].portal.company_owner_id == kwargs['member'].company_id else True}
        },
        MembersOrMembershipBase.STATUSES['APPLICANT']: {
            MembersOrMembershipBase.ACTIONS['WITHDRAW']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]}},
        MembersOrMembershipBase.STATUSES['SUSPENDED']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]}},
        MembersOrMembershipBase.STATUSES['FROZEN']: {
            MembersOrMembershipBase.ACTIONS['UNSUBSCRIBE']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]},
            MembersOrMembershipBase.ACTIONS['RESTORE']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]}},
        MembersOrMembershipBase.STATUSES['REJECTED']: {
            MembersOrMembershipBase.ACTIONS['WITHDRAW']: {
                'employee': [UserCompany.RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]}},
        MembersOrMembershipBase.STATUSES['DELETED']: {}
    }

    def actions(self):
        return BaseRightsInProfireader.base_actions(self, UserCompany.get(company_id=self.company.id),
                                                    object=self.member_company)

    def action_is_allowed(self, action_name, employee):
        add_check = {'company_membership': self.member_company.portal.own_company} \
            if action_name == MembersOrMembershipBase.ACTIONS['FREEZE'] else {}
        return self.action_is_allowed_member_company(action_name, employee, add_check)


# THIS IS CLASSES FOR CHECK APPROPRIATE RULE

# base rights
class UserIsActive(BaseRightsInProfireader):
    def __init__(self, user=None):
        self.user = user if user else g.user

    def get_allowed_attributes(self, key, value):
        if key == 'user_id':
            key = 'user'
            value = User.get(value)
        return key, value

    def is_allowed(self, check_only_banned=None, raise_exception_redirect_if_not = False):
        if not self.user:
            raise Exception('nouser')
        return self.user.is_active(check_only_banned, raise_exception_redirect_if_not= raise_exception_redirect_if_not)


class UserNonBanned(UserIsActive):
    def __init__(self, user=None):
        super(UserNonBanned, self).__init__(user=user)

    def is_allowed(self, raise_exception_redirect_if_not = False):
        return UserIsActive.is_allowed(self, check_only_banned=True)


class AllowAll(BaseRightsInProfireader):
    def is_allowed(self, raise_exception_redirect_if_not = False):
        return True


class CanCreateCompanyRight(UserIsActive):
    pass


class UserEditProfieRight(BaseRightsInProfireader):
    def __init__(self, user=None):
        self.user = user if isinstance(user, User) else User.get(user) if user else None

    def get_allowed_attributes(self, key, value):
        if key == 'user_id':
            key = 'user'
            value = User.get(value)
        return key, value

    def is_allowed(self, raise_exception_redirect_if_not = False):
        if self.user == g.user:
            return self._is_action_allowed(self.user, self.ACTIONS['EDIT_USER_PROFILE'], {'user': self.user},
                                           actions=self.ACTIONS)
        else:
            return 'Bad data!'


# rights in filemanager

class CanUpload(FilemanagerRights):
    pass


# base rights employee in company

class UserIsEmployee(BaseRightsEmployeeInCompany):
    def __init__(self, company=None, material=None):
        super(UserIsEmployee, self).__init__(company=company)
        self.material = material if isinstance(material, Material) else Material.get(material) if material else None

    def is_allowed(self, raise_exception_redirect_if_not = False):
        self.company = self.company if self.company else self.material.company
        employee = UserCompany.get(company_id=self.company.id)
        if not employee:
            return "Sorry!You are not employee in this company!"
        return True


class EditCompanyRight(BaseRightsEmployeeInCompany):
    def is_allowed(self, raise_exception_redirect_if_not = False):
        return self.action_is_allowed(self.ACTIONS['EDIT_COMPANY'])


class EditPortalRight(BaseRightsEmployeeInCompany):
    def __init__(self, company=None, portal=None):
        super(EditPortalRight, self).__init__(company=company)
        self.portal = portal

    def is_allowed(self, raise_exception_redirect_if_not = False):
        if self.company == None and self.portal:
            self.company = self.portal.own_company
        return self.action_is_allowed(self.ACTIONS['EDIT_PORTAL'])


class RequireMembereeAtPortalsRight(BaseRightsEmployeeInCompany):
    def is_allowed(self, raise_exception_redirect_if_not = False):
        return self.action_is_allowed(self.ACTIONS['COMPANY_REQUIRE_MEMBEREE_AT_PORTALS'])


class PortalManageMembersCompaniesRight(BaseRightsEmployeeInCompany):
    def __init__(self, company=None, member_id=None):
        super(PortalManageMembersCompaniesRight, self).__init__(company=company)
        self.member_id = member_id

    def is_allowed(self, raise_exception_redirect_if_not = False):
        if self.company.id == self.member_id:
            return False
        return self.action_is_allowed(self.ACTIONS['PORTAL_MANAGE_MEMBERS_COMPANIES'])


class EmployeeAllowRight(EmployeesRight):
    def __init__(self, company=None, user=None):
        super(EmployeeAllowRight, self).__init__(company=company)
        self.user = user

    def is_allowed(self, raise_exception_redirect_if_not = False):
        self.employment = UserCompany.get(user_id=self.user.id, company_id=self.company.id)
        return self.action_is_allowed(self.ACTIONS['ALLOW'])


# rights for work with articles

class CanMaterialBePublished(PublishUnpublishInPortal):
    pass


class EditMaterialRight(EditOrSubmitMaterialInPortal):
    def is_allowed(self, raise_exception_redirect_if_not = False):
        return self.action_is_allowed(self.ACTIONS['EDIT'])


class EditPublicationRight(PublishUnpublishInPortal):
    def __init__(self, publication=None, company=None):
        super(EditPublicationRight, self).__init__(publication=publication, company=company)

    def is_allowed(self, raise_exception_redirect_if_not = False):
        self.division = self.publication.division
        return self.actions()[self.ACTIONS['EDIT']]


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
                                    lambda a: not (inspect.isroutine(a)))
    if not with_values:
        return [a[0] for a in attributes if
                not (a[0].startswith('__') and a[0].endswith('__'))]
    else:
        return [a for a in attributes if
                not (a[0].startswith('__') and a[0].endswith('__'))]


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
    MANAGE_COMPANIES_MEMBERS = (
    'manage_companies_members', 0x01000, 'Accept or refuse company membership on portal', 17)

    # read this:
    # http://stackoverflow.com/questions/9058305/getting-attributes-of-a-class
    @classmethod
    def keys(cls, with_values=False):
        attributes = inspect.getmembers(cls, lambda a: not (inspect.isroutine(a)))
        if not with_values:
            return [a[0] for a in attributes if
                    not (a[0].startswith('__') and a[0].endswith('__'))]
        else:
            return [a for a in attributes if
                    not (a[0].startswith('__') and a[0].endswith('__'))]

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
                [cls.VALUE_RIGHT()[2 ** position] for position, right in
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


# we really need RightAtomic to be inherited from dict.
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
