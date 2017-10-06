import re
from flask import g
from flask import url_for
from sqlalchemy import Column, ForeignKey, and_, or_, desc, text
from sqlalchemy.orm import relationship
from .elastic import PRElasticDocument
from .files import FileImageCrop, FileImgDescriptor
from .files import YoutubePlaylist
from .pr_base import PRBase, Base, Grid
from .users import User
from ..constants.RECORD_IDS import FOLDER_AND_FILE
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..constants.NOTIFICATIONS import NotifyEmploymentChange, NotifyCompanyEmployees
from ..models.portal import Portal, MemberCompanyPortal, UserPortalReader
from profapp import utils
from profapp.models.permissions import RIGHT_AT_COMPANY


class Company(Base, PRBase, NotifyCompanyEmployees, PRElasticDocument):
    __tablename__ = 'company'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    name = Column(TABLE_TYPES['name'], unique=True, nullable=False, default='')

    # _delme_logo_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=True)

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImageCrop.id), nullable=True)
    logo_file_img = relationship(FileImageCrop, uselist=False)
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
    web = Column(TABLE_TYPES['string_100'], nullable=True, default='')
    short_description = Column(TABLE_TYPES['text'], nullable=False, default='')
    about = Column(TABLE_TYPES['text'], nullable=False, default='')

    STATUSES = {
        'COMPANY_ACTIVE': 'COMPANY_ACTIVE',
        'COMPANY_SUSPENDED_BY_USER': 'COMPANY_SUSPENDED_BY_USER'
    }

    status = Column(TABLE_TYPES['status'], nullable=False, default=STATUSES['COMPANY_ACTIVE'])

    lat = Column(TABLE_TYPES['float'], nullable=True, default=49.8418907)
    lon = Column(TABLE_TYPES['float'], nullable=True, default=24.0316261)

    portal_members = relationship(MemberCompanyPortal, uselist=True)

    own_portal = relationship(Portal,
                              back_populates='own_company', uselist=False,
                              foreign_keys='Portal.company_owner_id')

    author_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id), nullable=False)
    user_owner = relationship(User, back_populates='companies')

    employments = relationship('UserCompany', back_populates='company')

    employments_objectable_for_company = relationship('UserCompany',
                                                      viewonly=True,
                                                      primaryjoin="and_(Company.id == UserCompany.company_id, or_(UserCompany.status == 'EMPLOYMENT_ACTIVE', UserCompany.status == 'EMPLOYMENT_REQUESTED_BY_USER', UserCompany.status == 'EMPLOYMENT_SUSPENDED_BY_COMPANY'))")

    users_employee_active = relationship('User',
                                          viewonly=True,
                                          primaryjoin="and_(Company.id == UserCompany.company_id, UserCompany.status == 'EMPLOYMENT_ACTIVE')",
                                          secondary='user_company',
                                          secondaryjoin="and_(UserCompany.user_id == User.id, User.status == 'COMPANY_ACTIVE')")

    memberships_active = relationship('MemberCompanyPortal',
                                          viewonly=True,
                                          primaryjoin="and_(Company.id == MemberCompanyPortal.company_id, MemberCompanyPortal.status == 'MEMBERSHIP_ACTIVE')",
                                          secondary='member_company_portal',
                                          secondaryjoin="and_(MemberCompanyPortal.portal_id == Portal.id, Portal.status == 'PORTAL_ACTIVE')")

    news_feeds = relationship('NewsFeedCompany', cascade="all, merge, delete-orphan")

    @staticmethod
    def get_portals_for_company(company_id):
        return g.db.query(Portal).outerjoin(MemberCompanyPortal, and_(MemberCompanyPortal.portal_id == Portal.id,
                                                                      MemberCompanyPortal.company_id == company_id)). \
            filter(MemberCompanyPortal.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']). \
            filter(Portal.status.in_([Portal.STATUSES['PORTAL_ACTIVE']]))

    def __init__(self, **kwargs):
        # TODO: OZ by OZ: check default value for all columns
        if 'lon' not in kwargs:
            kwargs['lon'] = self.__table__.c.lon.default.arg
        if 'lat' not in kwargs:
            kwargs['lat'] = self.__table__.c.lat.default.arg
        Base.__init__(self, **kwargs)

    youtube_playlists = relationship('YoutubePlaylist')

    def is_active(self):
        if self.status != Company.STATUSES['COMPANY_ACTIVE']:
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
        if not utils.is_email(str(self.email)):
            ret['errors']['email'] = 'Invalid email address'

        self.web = self.web.strip()
        print(self.web)
        if self.web and not utils.is_url(self.web):
            ret['errors']['web'] = 'Invalid web address'
        if not re.match('[^\s]{3,}', self.name):
            ret['errors']['name'] = 'Your Company name must be at least 3 characters long.'
        self.phone = re.sub(r'[ ]*', '', self.phone)

        if not re.match('^\+[0-9]{2}(([0-9]{3})|(\([0-9]{3}\)))(([\.\-])?[0-9]){7}$', self.phone):
            ret['errors']['phone'] = 'pls enter a correct number in format +38 099 11 22 333'
        else:
            self.phone = re.sub(r'[()]*', '', self.phone)
            self.phone = self.phone[0:3] + ' ' + self.phone[3:6] + ' ' + self.phone[6:9] + ' ' + \
                         self.phone[10:11] + ' ' + self.phone[12:13]

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
        from profapp.models.permissions import RIGHT_AT_COMPANY

        user_company = UserCompany(status=UserCompany.STATUSES['EMPLOYMENT_ACTIVE'], rights={RIGHT_AT_COMPANY._OWNER:
                                                                                                 True})
        user_company.user = g.user
        user_company.company = self
        g.user.employments.append(user_company)
        g.user.companies.append(self)
        self.youtube_playlists.append(YoutubePlaylist(name=self.name, company_owner=self))
        self.save()

        return self

    @staticmethod
    def search_for_company_to_employ(searchtext, ignore_ids=[]):
        return g.db.query(Company). \
            outerjoin(UserCompany, and_(UserCompany.company_id == Company.id, UserCompany.user_id == g.user.id)). \
            filter(Company.name.ilike("%" + searchtext + "%")). \
            filter(or_(
            UserCompany.status.in_(UserCompany.DELETED_STATUSES),
            UserCompany.status == None)). \
            filter(Company.status.in_([Company.STATUSES['COMPANY_ACTIVE']])). \
            filter(~Company.id.in_(ignore_ids)).order_by(Company.name)

    def get_client_side_dict(self,
                             fields='id,name,author_user_id,country,region,address,phone,phone2,email,web,postcode,city,'
                                    'short_description,journalist_folder_file_id,logo,about,lat,lon,'
                                    'own_portal.id|host',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def get_allowed_statuses(company_id=None, portal_id=None):
        if company_id:
            sub_query = utils.db.query_filter(MemberCompanyPortal, company_id=company_id).filter(
                MemberCompanyPortal.status != "DELETED").all()
        else:
            sub_query = utils.db.query_filter(MemberCompanyPortal, portal_id=portal_id)
        return sorted(list({partner.status for partner in sub_query}))

    def get_rights_for_current_user(self):
        employment = UserCompany.get_by_user_and_company_ids(company_id=self.id)
        return employment.rights if employment else None

    def get_user_with_rights(self, *rights_sets, get_text_representation=False):
        from ..models.permissions import RIGHT_AT_COMPANY
        # TODO: OZ by OZ: use operator overloading (&,|) instead of list(|),set(&)
        if not rights_sets:
            return []

        or_conditions = []
        for rights_set in rights_sets:
            if isinstance(rights_set, str):
                rights_set = set([rights_set])
            binary = RIGHT_AT_COMPANY._tobin({r: True for r in rights_set})
            or_conditions.append("(%s = (rights & %s))" % (binary, binary))

        usrc = g.db.query(UserCompany).\
            filter(~UserCompany.status.in_(UserCompany.DELETED_STATUSES)).\
            filter(UserCompany.company_id == self.id).\
            filter(text("(" + " OR ".join(or_conditions) + ")")).all()

        return g.db.query(User).filter(User.id.in_([e.user_id for e in usrc])).all()

    @staticmethod
    def subquery_portal_banners(company_id, filters):
        sub_query = utils.db.query_filter(MemberCompanyPortal, company_id=company_id)

    @staticmethod
    def subquery_portal_partners(company_id, filters, filters_exсept=None):
        sub_query = utils.db.query_filter(MemberCompanyPortal, company_id=company_id)
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
            sub_query = Grid.subquery_grid(sub_query, list_filters,
                                           sorts=[{'value': 'asc', 'field': MemberCompanyPortal.id}])
        return sub_query

    @staticmethod
    def subquery_company_partners(company_id, filters, filters_exсept=None):
        sub_query = utils.db.query_filter(MemberCompanyPortal, portal_id=utils.db.query_filter(Portal,
                                                                                               company_owner_id=company_id).subquery().c.id).order_by(
            desc(MemberCompanyPortal.id))
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

    from profapp.constants.NOTIFICATIONS import NOTIFICATION_TYPES

    def _send_notification_about_company_changes(self, text, dictionary={},
                                               rights_at_company = RIGHT_AT_COMPANY._ANY,
                                               more_phrases_to_company=[],
                                               notification_type_to_company=NOTIFICATION_TYPES['COMPANY_ACTIVITY'],
                                               comment=None, except_to_user=None):

        from ..models.translate import Phrase

        phrase_comment = (' when ' + comment) if comment else ''

        more_phrases_to_company = more_phrases_to_company if isinstance(more_phrases_to_company, list) else [
            more_phrases_to_company]


        # grid_url = lambda endpoint, **kwargs: utils.jinja.grid_url(self.id, endpoint=endpoint, **kwargs)

        default_dict = {
            'company': self,
            'url_company_profile': url_for('company.profile', company_id=self.id),
        }

        if getattr(g, 'user', None):
            user_who_made_changes_phrase = "User " + utils.jinja.link_user_profile() + " at "
            except_to_user = utils.set_default(except_to_user, [g.user])
            default_dict['url_user_profile'] = url_for('user.profile', user_id=g.user.id)
        else:
            user_who_made_changes_phrase = 'At '
            except_to_user = utils.set_default(except_to_user, [])


        all_dictionary_data = utils.dict_merge(default_dict, dictionary)

        phrase_to_employees_at_company = Phrase(
            user_who_made_changes_phrase + "%s of user %s at your company %s just happened following: " % \
            (utils.jinja.link_company_profile(),) + text, dict=all_dictionary_data,
            comment="to company employees with rights %s%s" % (','.join(rights_at_company), phrase_comment))

        from ..models.messenger import Socket

        Socket.prepare_notifications(
            self.company.get_user_with_rights(rights_at_company),
            notification_type_to_company,
            [phrase_to_employees_at_company] + more_phrases_to_company, except_to_user=except_to_user)

        return lambda: utils.do_nothing()


class UserCompany(Base, PRBase, NotifyEmploymentChange):

    __tablename__ = 'user_company'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)

    # TODO: OZ by OZ: remove `SUSPENDED` status from db type

    STATUSES = {'EMPLOYMENT_REQUESTED_BY_USER': 'EMPLOYMENT_REQUESTED_BY_USER',
                'EMPLOYMENT_REQUESTED_BY_COMPANY': 'EMPLOYMENT_REQUESTED_BY_COMPANY',
                'EMPLOYMENT_ACTIVE': 'EMPLOYMENT_ACTIVE',
                'EMPLOYMENT_SUSPENDED_BY_USER': 'EMPLOYMENT_SUSPENDED_BY_USER',
                'EMPLOYMENT_SUSPENDED_BY_COMPANY': 'EMPLOYMENT_SUSPENDED_BY_COMPANY',
                'EMPLOYMENT_CANCELED_BY_USER': 'EMPLOYMENT_CANCELED_BY_USER',
                'EMPLOYMENT_CANCELED_BY_COMPANY': 'EMPLOYMENT_CANCELED_BY_COMPANY',
                }

    DELETED_STATUSES = [STATUSES['EMPLOYMENT_CANCELED_BY_USER'], STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']]

    def status_changes_by_company(self):
        from ..models.permissions import RIGHT_AT_COMPANY

        r = UserCompany.get_by_user_and_company_ids(company_id=self.company_id).rights[
            RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE]

        if not r:
            return False

        changes = {s: {'status': s, 'enabled': r, 'message': ''} for s in UserCompany.STATUSES}

        if self.user_id == self.company.author_user_id:
            changes[UserCompany.STATUSES[
                'EMPLOYMENT_CANCELED_BY_COMPANY']]['message'] = 'You can`t cancel owner employment'
            changes[UserCompany.STATUSES[
                'EMPLOYMENT_CANCELED_BY_COMPANY']]['enabled'] = False
            changes[UserCompany.STATUSES[
                'EMPLOYMENT_SUSPENDED_BY_COMPANY']]['message'] = 'You can`t suspend owner employment'
            changes[UserCompany.STATUSES[
                'EMPLOYMENT_SUSPENDED_BY_COMPANY']]['enabled'] = False

        if self.status == UserCompany.STATUSES['EMPLOYMENT_ACTIVE']:
            return [
                changes[UserCompany.STATUSES['EMPLOYMENT_SUSPENDED_BY_COMPANY']],
                changes[UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']],
            ]
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_REQUESTED_BY_COMPANY']:
            return [
                changes[UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']],
            ]
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_REQUESTED_BY_USER']:
            return [
                changes[UserCompany.STATUSES['EMPLOYMENT_ACTIVE']],
                changes[UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']],
            ]
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_SUSPENDED_BY_COMPANY']:
            return [
                changes[UserCompany.STATUSES['EMPLOYMENT_ACTIVE']],
                changes[UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']],
            ]
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_SUSPENDED_BY_USER']:
            return [
                changes[UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']]
            ]
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_COMPANY']:
            return []
        elif self.status == UserCompany.STATUSES['EMPLOYMENT_CANCELED_BY_USER']:
            return []

    status = Column(TABLE_TYPES['status'])

    position = Column(TABLE_TYPES['short_name'], default='')

    md_tm = Column(TABLE_TYPES['timestamp'])
    works_since_tm = Column(TABLE_TYPES['timestamp'])

    # banned = Column(TABLE_TYPES['boolean'], default=False, nullable=False)

    rights = Column(TABLE_TYPES['binary_rights'](RIGHT_AT_COMPANY),
                    default={RIGHT_AT_COMPANY.FILES_BROWSE: True, RIGHT_AT_COMPANY.ARTICLES_SUBMIT_OR_PUBLISH: True},
                    nullable=False)

    company = relationship(Company, back_populates='employments')
    user = relationship('User', back_populates='employments')

    @staticmethod
    def apply_user_to_company(company_id):
        from profapp.models.permissions import RIGHT_AT_COMPANY
        # TODO: OZ by OZ: reset rights after rejoining to company
        employment = UserCompany.get_by_user_and_company_ids(company_id=company_id) or \
                     UserCompany(user=g.user, company=Company.get(company_id))

        if not employment.status or employment.status in UserCompany.DELETED_STATUSES:
            employment.status = UserCompany.STATUSES['EMPLOYMENT_REQUESTED_BY_USER']
            employment.save()
            employment.NOTIFY_USER_APPLIED()

        return employment

    def is_active(self):
        if self.status != UserCompany.STATUSES['EMPLOYMENT_ACTIVE']:
            return False
        return True

    def get_client_side_dict(self, fields='id,user_id,company_id,position,status,rights', more_fields=None):
        return self.to_dict(fields, more_fields)

    # def set_client_side_dict(self, json):
    #     self.attr(utils.filter_json(json, 'status|position|rights'))

    def employees_grid_row(self):
        return {
            'id': self.id,
            'status_changes': self.status_changes_by_company(),
            'employment': self.get_client_side_dict(
                more_fields='company.name|id,user.full_name|address_email|address_phone'),
        }

    @staticmethod
    def get_by_user_and_company_ids(user_id=None, company_id=None):
        return utils.db.query_filter(UserCompany).filter_by(
            user_id=(g.user.id if g.user else '') if user_id is None else user_id,
            company_id=company_id).first()

    # @staticmethod
    # def apply_request(company_id, user_id, bool):
    #     """Method which define when employer apply or reject request from some user to
    #     subscribe to this company. If bool == True(Apply) - update rights to basic rights in company
    #     and status to active, If bool == False(Reject) - just update status to rejected."""
    #     if bool == 'True':
    #         stat = UserCompany.STATUSES['EMPLOYMENT_ACTIVE']
    #         UserCompany.update_rights(user_id, company_id, UserCompany.RIGHTS_AT_COMPANY_DEFAULT)
    #     else:
    #         stat = UserCompany.STATUSES['REJECTED']
    #
    #     utils.db.query_filter(UserCompany, company_id=company_id, user_id=user_id,
    #                           status=UserCompany.STATUSES['APPLICANT']).update({'status': stat})

    def has_rights(self, rightname):
        if self.company.user_owner.id == self.user_id:
            return True

        if rightname == '_OWNER':
            return rightname
        if rightname == '_ANY':
            return True if self.status == self.STATUSES['EMPLOYMENT_ACTIVE'] else rightname
        else:
            return True if (self.status == self.STATUSES['EMPLOYMENT_ACTIVE'] and self.rights[rightname]) else rightname

    @staticmethod
    def search_for_user_to_join(company_id, searchtext):
        """Return all users in current company which have characters
        in their name like searchtext"""
        return [user.get_client_side_dict(fields='full_name|id') for user in
                utils.db.query_filter(User).filter(
                    ~utils.db.query_filter(UserCompany, user_id=User.id, company_id=company_id).exists()).
                    filter(User.full_name.ilike("%" + searchtext + "%")).all()]


    from profapp.constants.NOTIFICATIONS import NOTIFICATION_TYPES

    def _send_notification_about_employment_change(self, text, dictionary={},
                                               rights_at_company = RIGHT_AT_COMPANY.EMPLOYEE_ENLIST_OR_FIRE,
                                               more_phrases_to_company=[],
                                               more_phrases_to_user=[],
                                               notification_type_to_company=NOTIFICATION_TYPES['EMPLOYMENT_COMPANY_ACTIVITY'],
                                               notification_type_to_user=NOTIFICATION_TYPES['EMPLOYMENT_USER_ACTIVITY'],
                                                   comment=None, except_to_user=None):

        from ..models.translate import Phrase

        phrase_comment = (' when ' + comment) if comment else ''


        more_phrases_to_company = more_phrases_to_company if isinstance(more_phrases_to_company, list) else [
            more_phrases_to_company]

        more_phrases_to_user = more_phrases_to_user if isinstance(more_phrases_to_user, list) else [
            more_phrases_to_user]

        grid_url = lambda endpoint, **kwargs: utils.jinja.grid_url(self.id, endpoint=endpoint, **kwargs)

        default_dict = {
            'company': self.company,
            'employee': self.user,
            'url_company_profile': url_for('company.profile', company_id=self.company_id),
            'url_company_employees': grid_url('company.employees', company_id=self.company_id),
            # 'url_user_employers': grid_url('user.employers', user_id=self.user_id),
            'url_employee_user_profile': url_for('user.profile', user_id=self.user_id),
        }

        if getattr(g, 'user', None):
            user_who_made_changes_phrase = "User " + utils.jinja.link_user_profile() + " at "
            except_to_user = utils.set_default(except_to_user, [g.user])
            default_dict['url_user_profile'] = url_for('user.profile', user_id=g.user.id)
        else:
            user_who_made_changes_phrase = 'At '
            except_to_user = utils.set_default(except_to_user, [])


        all_dictionary_data = utils.dict_merge(default_dict, dictionary)

        phrase_to_employees_at_company = Phrase(
            user_who_made_changes_phrase + "%s of user %s at your company %s just happened following: " % \
            (utils.jinja.link('url_company_employees', 'employment', True),
             utils.jinja.link('url_employee_user_profile', 'employee.full_name'),
             utils.jinja.link_company_profile()) + text, dict=all_dictionary_data,
            comment="to company employees with rights %s%s" % (
                ','.join(rights_at_company), phrase_comment))

        phrase_to_user = Phrase(
            user_who_made_changes_phrase + "your %s at company %s just made following: " % \
            (utils.jinja.link('url_company_employees', 'employment', True),
            utils.jinja.link_company_profile()) +
            text, dict=all_dictionary_data,
            comment="to employee user on employment changes%s" % (phrase_comment,))

        from ..models.messenger import Socket

        Socket.prepare_notifications(
            self.company.get_user_with_rights(rights_at_company),
            notification_type_to_company,
            [phrase_to_employees_at_company] + more_phrases_to_company, except_to_user=except_to_user)

        Socket.prepare_notifications(
            [self.user],
            notification_type_to_user,
            [phrase_to_user] + more_phrases_to_user, except_to_user=except_to_user)

        return lambda: utils.do_nothing()


class NewsFeedCompany(Base, PRBase):
    __tablename__ = 'company_news_feed'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)

    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)
    company = relationship('Company', foreign_keys=[company_id])

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])


    type = Column(TABLE_TYPES['string_10'])
    name = Column(TABLE_TYPES['string_100'])

    source = Column(TABLE_TYPES['string_1000'])

    update_interval_seconds = Column(TABLE_TYPES['timestamp'], default=3600)

    last_pull_tm = Column(TABLE_TYPES['timestamp'])


    @staticmethod
    def subquery_company_news_feed(company_id=None, filters=None, sorts=None):
        sub_query = utils.db.query_filter(NewsFeedCompany, company_id=company_id)
        return sub_query

    def validate(self, is_new=False):
        ret = super().validate(is_new=is_new, regexps={'name': '[^\s]{3,}'})
        print(self.source)
        if not utils.is_url(self.source):
            ret['errors']['source'] = 'Invalid url'
        return ret

    def get_client_side_dict(self, fields='id,company_id,name,source,type,cr_tm', more_fields=None):
        return self.to_dict(fields, more_fields)

    # def news_feed_grid_row(self):
    #     ret = self.get_client_side_dict(fields='name,md_tm,id,source,type')
    #
    #     from sqlalchemy.sql import functions
    #
    #     cnt = g.db.query(Publication.status, Publication.visibility,
        #                  functions.count(NewsFeedCompany.id).label('cnt')). \
        #     join(Material, and_(Publication.material_id == Material.id, Material.id == self.id)). \
        #     group_by(Publication.status, Publication.visibility).all()
        #
        # ret['publications'] = Publication.group_by_status_and_visibility(cnt)
        # return ret
