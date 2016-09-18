from sqlalchemy import Column, String, ForeignKey, UniqueConstraint, Enum  # , update
from sqlalchemy.orm import relationship, backref
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from flask.ext.login import current_user
from sqlalchemy import Column, String, ForeignKey, update, and_
from sqlalchemy.orm import relationship
from ..constants.TABLE_TYPES import TABLE_TYPES, BinaryRights
from flask import g
from config import Config
from utils.db_utils import db
from sqlalchemy import CheckConstraint
from flask import abort
from .pr_base import PRBase, Base, Search, Grid
from ..controllers import errors
from functools import wraps
from .files import YoutubePlaylist
from ..constants.SEARCH import RELEVANCE
from .users import User
from ..models.portal import Portal, MemberCompanyPortal, UserPortalReader
from .. import utils
import re
from .files import FileImg, FileImgDescriptor
from .elastic import PRElasticDocument


class Company(Base, PRBase, PRElasticDocument):
    __tablename__ = 'company'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    name = Column(TABLE_TYPES['name'], unique=True, nullable=False, default='')

    _delme_logo_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=True)

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    logo_file_img = relationship(FileImg, uselist=False)
    logo = FileImgDescriptor(relation_name='logo_file_img',
                             file_decorator=lambda c, r, f: f.attr(
                                 name='%s_for_company_logo_%s' % (f.name, c.id),
                                 parent_id=c.system_folder_file_id,
                                 root_folder_id=c.system_folder_file_id),
                             image_size=[480, 480],
                             min_size=[100, 100],
                             aspect_ratio=[0.25, 4.],
                             no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_company_logo()))

    journalist_folder_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)
    system_folder_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)

    country = Column(TABLE_TYPES['name'], nullable=False, default='')
    region = Column(TABLE_TYPES['name'], nullable=False, default='')
    city = Column(TABLE_TYPES['name'], nullable=False, default='')
    postcode = Column(TABLE_TYPES['name'], nullable=False, default='')
    address = Column(TABLE_TYPES['name'], nullable=False, default='')
    phone = Column(TABLE_TYPES['phone'], nullable=False, default='')
    phone2 = Column(TABLE_TYPES['phone'], nullable=False, default='')
    email = Column(TABLE_TYPES['email'], nullable=False, default='')
    short_description = Column(TABLE_TYPES['text'], nullable=False, default='')
    about = Column(TABLE_TYPES['text'], nullable=False, default='')

    STATUSES = {'ACTIVE': 'ACTIVE', 'SUSPENDED': 'SUSPENDED'}
    status = Column(TABLE_TYPES['status'], nullable=False, default=STATUSES['ACTIVE'])

    lat = Column(TABLE_TYPES['float'], nullable=True, default=49.8418907)
    lon = Column(TABLE_TYPES['float'], nullable=True, default=24.0316261)

    portal_members = relationship(MemberCompanyPortal, uselist=True)

    own_portal = relationship(Portal,
                              back_populates='own_company', uselist=False,
                              foreign_keys='Portal.company_owner_id')

    # member_portal_plan = relationship('Portal',
    #                           back_populates='own_company', uselist=False,
    #                           foreign_keys='Portal.company_owner_id')

    author_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id), nullable=False)
    user_owner = relationship(User, back_populates='companies')

    # search_fields = {'name': {'relevance': lambda field='name': RELEVANCE.name},
    #                  'short_description': {'relevance': lambda field='short_description': RELEVANCE.short_description},
    #                  'about': {'relevance': lambda field='about': RELEVANCE.about},
    #                  'country': {'relevance': lambda field='country': RELEVANCE.country},
    #                  'phone': {'relevance': lambda field='phone': RELEVANCE.phone}}

    # TODO: AA by OZ: we need employees.position (from user_company table) (also search and fix #ERROR employees.position.2#)
    # ERROR employees.position.1#
    employments = relationship('UserCompany', back_populates='company')

    def __init__(self, **kwargs):
        # TODO: OZ by OZ: check default value for all columns
        if 'lon' not in kwargs:
            kwargs['lon'] = self.__table__.c.lon.default.arg
        if 'lat' not in kwargs:
            kwargs['lat'] = self.__table__.c.lat.default.arg
        Base.__init__(self, **kwargs)

    youtube_playlists = relationship('YoutubePlaylist')

    # # todo: add company time creation
    # logo_file_relationship = relationship('File',
    #                                       uselist=False,
    #                                       backref='logo_owner_company',
    #                                       foreign_keys='Company.logo_file_id')

    def is_active(self):
        if self.status != Company.STATUSES['ACTIVE']:
            return False
        return True

    def get_readers_for_portal(self, filters):
        query = g.db.query(User).join(UserPortalReader).join(UserPortalReader.portal).join(Portal.own_company).filter(
            Company.id == self.id)
        list_filters = []
        if filters:
            for filter in filters:
                list_filters.append({'type': 'text', 'value': filters[filter], 'field': eval("User." + filter)})
        query = Grid.subquery_grid(query, list_filters)
        return query

    def validate(self, is_new):
        ret = super().validate(is_new)
        if not re.match(r'[^\s]{3}', str(self.country)):
            ret['errors']['country'] = 'Your Country name must be at least 3 characters long.'
        if not re.match(r'[^\s]{3}', str(self.region)):
            ret['errors']['region'] = 'Your Region name must be at least 3 characters long.'
        if not re.match(r'[^\s]{3}', str(self.city)):
            ret['errors']['city'] = 'Your City name must be at least 3 characters long.'
        if not re.match(r'^[a-zA-Z0-9_.+-]{4,}', str(self.postcode)):
            ret['errors']['postcode'] = 'Your Postcode must be at least 4 digits or characters long.'
        if not re.match(r'[^\s]{3}', str(self.address)):
            ret['errors']['address'] = 'Your Address must be at least 3 characters long.'
        if not re.match(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)", str(self.email)):
            ret['errors']['email'] = 'Invalid email address'
        if not re.match('[^\s]{3,}', self.name):
            ret['errors']['name'] = 'Your Company name must be at least 3 characters long.'
        # phone validation
        if not re.match('^\+?[0-9]{3}-?[0-9]{6,12}$', self.phone):
            ret['errors']['phone'] = 'pls enter a correct number'

        self.lon = PRBase.str2float(self.lon)
        self.lat = PRBase.str2float(self.lat)

        if self.lon is not None or self.lat is not None:
            if self.lon is None or not utils.putInRange(self.lon, -180, 180, check_only=True):
                ret['errors']['lon'] = 'pls longitude in range [-180,180]'
            if self.lat is None or not utils.putInRange(self.lat, -90, 90, check_only=True):
                ret['errors']['lat'] = 'pls latitude in range [-90,90]'

        # if (self.lat is None and self.lon is not None) or (self.lat is not None and self.lon is None):
        #     ret['errors']['lon_lat'] = 'pls enter both lon and lat or none of them'

        return ret

    @property
    def readers_query(self):
        return g.db.query(User.id,
                          User.address_email,
                          User.full_name,
                          User.first_name,
                          User.last_name
                          ). \
            join(UserPortalReader). \
            join(Portal). \
            join(self.__class__). \
            order_by(User.full_name). \
            filter(self.__class__.id == self.id)

        # get all users in company : company.user_employees
        # get all users companies : user.company_employers

    # TODO: VK by OZ I think this have to be moved to __init__ and duplication check to validation
    def setup_new_company(self):
        """Add new company to company table and make all necessary relationships,
        if company with this name already exist raise DublicateName"""
        if db(Company, name=self.name).count():
            raise errors.DublicateName({
                'message': 'Company name %(name)s already exist. Please choose another name',
                'data': self.get_client_side_dict()})

        user_company = UserCompany(status=UserCompany.STATUSES['ACTIVE'], rights={UserCompany.RIGHT_AT_COMPANY._OWNER:
                                                                                      True})
        user_company.user = g.user
        user_company.company = self
        g.user.employments.append(user_company)
        g.user.companies.append(self)
        self.youtube_playlists.append(YoutubePlaylist(name=self.name, company_owner=self))
        self.save()

        return self

    @staticmethod
    def query_company(company_id):
        """Method return one company"""
        ret = db(Company, id=company_id).one()
        return ret

    @staticmethod
    def search_for_company(user_id, searchtext):
        """Return all companies which are not current user employers yet"""
        query_companies = db(Company).filter(
            Company.name.ilike("%" + searchtext + "%")).filter.all()
        ret = []
        for x in query_companies:
            ret.append(x.dict())

        return ret
        # return PRBase.searchResult(query_companies)

        # @staticmethod
        # def update_comp(company_id, data):
        #     """Edit company. Pass to data parameters which will be edited"""
        #     company = db(Company, id=company_id)
        #     upd = {x: y for x, y in zip(data.keys(), data.values())}
        #     company.update(upd)

        # if passed_file:
        #     file = File(company_id=company_id,
        #                 parent_id=company.one().system_folder_file_id,
        #                 author_user_id=g.user_dict['id'],
        #                 name=passed_file.filename,
        #                 mime=passed_file.content_type)
        #     company.update(
        #         {'logo_file_id': file.upload(
        #             content=passed_file.stream.read(-1)).id}
        #     )
        # db_session.flush()


    def get_client_side_dict(self,
                             fields='id,name,author_user_id,country,region,address,phone,phone2,email,postcode,city,'
                                    'short_description,journalist_folder_file_id,logo,about,lat,lon,'
                                    'own_portal.id|host',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    # def get_logo_client_side_dict(self):
    #     return self.get_image_cropped_file(self.logo_file_properties(),
    #                                        db(FileImg, croped_image_id=self.logo_file_id).first())

    # def set_logo_client_side_dict(self, client_data):
    #     if client_data['selected_by_user']['type'] == 'preset':
    #         client_data['selected_by_user'] = {'type': 'none'}
    #     self.logo_file_id = self.set_image_cropped_file(self.logo_file_properties(),
    #                                                       client_data, self.logo_file_id, self.system_folder_file_id)
    #     return self

    @staticmethod
    def get_allowed_statuses(company_id=None, portal_id=None):
        if company_id:
            sub_query = db(MemberCompanyPortal, company_id=company_id).filter(
                MemberCompanyPortal.status != "DELETED").all()
        else:
            sub_query = db(MemberCompanyPortal, portal_id=portal_id)
        return sorted(list({partner.status for partner in sub_query}))

    @staticmethod
    def subquery_portal_banners(company_id, filters):
        sub_query = db(MemberCompanyPortal, company_id=company_id)

    @staticmethod
    def subquery_portal_partners(company_id, filters, filters_exсept=None):
        sub_query = db(MemberCompanyPortal, company_id=company_id)
        list_filters = []
        if filters_exсept:
            if 'status' in filters:
                list_filters.append(
                    {'type': 'multiselect', 'value': filters['status'], 'field': MemberCompanyPortal.status})
            else:
                sub_query = sub_query.filter(and_(MemberCompanyPortal.status != v for v in filters_exсept))
                # if filters:
                #     sub_query = sub_query.join(MemberCompanyPortal.portal)
                #     if 'portal.name' in filters:
                #         list_filters.append({'type': 'text', 'value': filters['portal.name'], 'field': Portal.name})
                #     if 'link' in filters:
                #         list_filters.append({'type': 'text', 'value': filters['link'], 'field': Portal.host})
                #     if 'company' in filters:
                #         sub_query = sub_query.join(Company, Portal.company_owner_id == Company.id)
                #         list_filters.append({'type': 'text', 'value': filters['company'], 'field': Company.name})
            sub_query = Grid.subquery_grid(sub_query, list_filters)
        return sub_query

    @staticmethod
    def subquery_company_partners(company_id, filters, filters_exсept=None):
        sub_query = db(MemberCompanyPortal, portal_id=db(Portal, company_owner_id=company_id).subquery().c.id)
        list_filters = [];
        list_sorts = []
        if filters_exсept:
            if 'member.status' in filters:
                list_filters.append(
                    {'type': 'multiselect', 'value': filters['member.status'], 'field': MemberCompanyPortal.status})
            else:
                sub_query = sub_query.filter(and_(MemberCompanyPortal.status != v for v in filters_exсept))
                # if filters:
                #     sub_query = sub_query.join(MemberCompanyPortal.portal)
                #     if 'portal.name' in filters:
                #         list_filters.append({'type': 'text', 'value': filters['portal.name'], 'field': Portal.name})
                #     if 'link' in filters:
                #         list_filters.append({'type': 'text', 'value': filters['link'], 'field': Portal.host})
                #     if 'company' in filters:
                #         sub_query = sub_query.join(Company, Portal.company_owner_id == Company.id)
                #         list_filters.append({'type': 'text', 'value': filters['company'], 'field': Company.name})
        sub_query = sub_query.join(MemberCompanyPortal.company)
        # list_sorts.append({'value': 'desc', 'field': Company.name})
        sub_query = Grid.subquery_grid(sub_query, filters=list_filters)
        return sub_query

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def elastic_insert(self):
        pass

    def elastic_update(self):
        for m in self.portal_members:
            m.elastic_update()

    def elastic_delete(self):
        for m in self.portal_members:
            m.elastic_delete()


class UserCompany(Base, PRBase):
    __tablename__ = 'user_company'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)

    # TODO: OZ by OZ: remove `SUSPENDED` status from db type
    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE', 'FIRED': 'FIRED'}
    status = Column(TABLE_TYPES['status'], default=STATUSES['APPLICANT'], nullable=False)

    class RIGHT_AT_COMPANY(BinaryRights):
        FILES_BROWSE = 4
        FILES_UPLOAD = 5
        FILES_DELETE_OTHERS = 14

        ARTICLES_SUBMIT_OR_PUBLISH = 8
        ARTICLES_EDIT_OTHERS = 12
        ARTICLES_DELETE = 19  # reset!
        ARTICLES_UNPUBLISH = 17  # reset!

        EMPLOYEE_ENLIST_OR_FIRE = 6
        EMPLOYEE_ALLOW_RIGHTS = 9

        COMPANY_REQUIRE_MEMBEREE_AT_PORTALS = 15
        COMPANY_EDIT_PROFILE = 1

        PORTAL_EDIT_PROFILE = 10
        PORTAL_MANAGE_READERS = 16
        PORTAL_MANAGE_COMMENTS = 18
        PORTAL_MANAGE_MEMBERS_COMPANIES = 13

    position = Column(TABLE_TYPES['short_name'], default='')

    md_tm = Column(TABLE_TYPES['timestamp'])
    works_since_tm = Column(TABLE_TYPES['timestamp'])

    banned = Column(TABLE_TYPES['boolean'], default=False, nullable=False)

    rights = Column(TABLE_TYPES['binary_rights'](RIGHT_AT_COMPANY),
                    default={RIGHT_AT_COMPANY.FILES_BROWSE: True, RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH: True},
                    nullable=False)

    # TODO: VK by OZ: custom collumn
    # company_logo = Column(TABLE_TYPES['image'](size=[100,200]),
    #                 default='324235423-423423',
    #                 nullable=False)

    company = relationship(Company, back_populates='employments')
    user = relationship('User', back_populates='employments')

    def __init__(self, user_id=None, company_id=None, status=STATUSES['APPLICANT'],
                 rights=None):

        super(UserCompany, self).__init__()
        self.user_id = user_id
        self.company_id = company_id
        self.status = status
        self.rights = {self.RIGHT_AT_COMPANY.FILES_BROWSE: True, self.RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH:
            True} if rights is None else rights

    def is_active(self):
        if self.status != UserCompany.STATUSES['ACTIVE']:
            return False
        return True

    @staticmethod
    # TODO: OZ by OZ: remove this func. use  get_by_user_and_company_ids instead
    def get(user_id=None, company_id=None):
        return db(UserCompany).filter_by(user_id=user_id if user_id else g.user.id, company_id=company_id).first()

    @staticmethod
    # TODO: OZ by OZ: rework this as in action-style
    def get_statuses_avaible(company_id):
        available_statuses = {s: True for s in UserCompany.STATUSES}
        user_rights = UserCompany.get(user_id=current_user.id, company_id=company_id).rights
        if user_rights['EMPLOYEE_ENLIST_OR_FIRE'] == False:
            available_statuses['ACTIVE'] = False
        if user_rights['EMPLOYEE_ENLIST_OR_FIRE'] == False:
            available_statuses['SUSPENDED'] = False
            available_statuses['UNSUSPEND'] = False
        return available_statuses

    def get_client_side_dict(self, fields='id,user_id,company_id,position,status,rights', more_fields=None):
        return self.to_dict(fields, more_fields)

    def set_client_side_dict(self, json):
        self.attr(g.filter_json(json, 'status|position|rights'))

    @staticmethod
    def get_by_user_and_company_ids(user_id=None, company_id=None):
        return db(UserCompany).filter_by(user_id=user_id if user_id else g.user.id, company_id=company_id).one()

    # TODO: VK by OZ: pls teach everybody what is done here
    # # do we provide any rights to user at subscribing? Not yet
    # def subscribe_to_company(self):
    #     """Add user to company with non-active status. After that Employer can accept request,
    #     and add necessary rights, or reject this user. Method need instance of class with
    #     parameters : user_id, company_id, status"""
    #     if db(UserCompany, user_id=self.user_id,
    #           company_id=self.company_id).count():
    #         raise errors.AlreadyJoined({
    #             'message': 'user already joined to company %(name)s',
    #             'data': self.get_client_side_dict()})
    #     self.employee = User.user_query(self.user_id)
    #     self.employer = db(Company, id=self.company_id).one()
    #     return self

    # @staticmethod
    # def change_status_employee(company_id, user_id, status=STATUSES['SUSPENDED']):
    #     """This method make status employee in this company suspended"""
    #     db(UserCompany, company_id=company_id, user_id=user_id). \
    #         update({'status': status})
    #     if status == UserCompany.STATUSES['FIRED']:
    #         UserCompany.update_rights(user_id=user_id,
    #                                   company_id=company_id,
    #                                   new_rights=()
    #                                   )
    #         # db_session.flush()

    @staticmethod
    def apply_request(company_id, user_id, bool):
        """Method which define when employer apply or reject request from some user to
        subscribe to this company. If bool == True(Apply) - update rights to basic rights in company
        and status to active, If bool == False(Reject) - just update status to rejected."""
        if bool == 'True':
            stat = UserCompany.STATUSES['ACTIVE']
            UserCompany.update_rights(user_id, company_id, UserCompany.RIGHTS_AT_COMPANY_DEFAULT)
        else:
            stat = UserCompany.STATUSES['REJECTED']

        db(UserCompany, company_id=company_id, user_id=user_id,
           status=UserCompany.STATUSES['APPLICANT']).update({'status': stat})

    def has_rights(self, rightname):
        if self.company.user_owner.id == self.user_id:
            return True

        # if rightname == 'ARTICLES_EDIT_OTHERS':
        #     if self.editor
        if rightname == '_OWNER':
            return rightname
        if rightname == '_ANY':
            return True if self.status == self.STATUSES['ACTIVE'] else rightname
        else:
            return True if (self.status == self.STATUSES['ACTIVE'] and self.rights[rightname]) else rightname

    @staticmethod
    def search_for_user_to_join(company_id, searchtext):
        """Return all users in current company which have characters
        in their name like searchtext"""
        return [user.get_client_side_dict(fields='full_name|id') for user in
                db(User).filter(~db(UserCompany, user_id=User.id, company_id=company_id).exists()).
                    filter(User.full_name.ilike("%" + searchtext + "%")).all()]

        # @staticmethod
        # def permissions(needed_rights_iterable, user_object, company_object):
        #
        #     needed_rights_int = Right.transform_rights_into_integer(needed_rights_iterable)
        #     # TODO: implement Anonymous User handling
        #     if not (user_object and company_object):
        #         raise errors.ImproperRightsDecoratorUse
        #
        #     user = user_object
        #     company = company_object
        #     if type(user_object) is str:
        #         user = g.db.query(User).filter_by(id=user_object).first()
        #         if not user:
        #             return abort(400)
        #     if type(company_object) is str:
        #         company = g.db.query(Company).filter_by(id=company_object).first()
        #         if not company:
        #             return abort(400)
        #
        #     user_company = user.company_employers.filter_by(company_id=company.id).first()
        #
        #     if not user_company:
        #         return False if needed_rights_iterable else True
        #
        #     if user_company.banned:  # or user_company.status != STATUS.ACTIVE():
        #         return False
        #
        #     if user_company:
        #         available_rights = user_company.rights_int
        #     else:
        #         return False
        #         # available_rights = 0
        #
        #     return True if available_rights & needed_rights_int == needed_rights_int else False
