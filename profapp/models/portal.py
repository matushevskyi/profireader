from ..constants.TABLE_TYPES import TABLE_TYPES, BinaryRights
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from flask import g
from utils.db_utils import db
from .pr_base import PRBase, Base
import re
from ..constants.SEARCH import RELEVANCE
from sqlalchemy import orm
from config import Config
import simplejson
from .files import File, FileImg, FileImgDescriptor
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from .. import utils
from ..models.tag import Tag, TagMembership
from profapp.controllers.errors import BadDataProvided
import datetime
import json
from functools import reduce
from sqlalchemy.sql import and_
from .elastic import PRElasticField, PRElasticDocument


class Portal(Base, PRBase):
    __tablename__ = 'portal'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False,
                primary_key=True)
    name = Column(TABLE_TYPES['name'])
    host = Column(TABLE_TYPES['short_name'])
    lang = Column(TABLE_TYPES['short_name'])

    url_facebook = Column(TABLE_TYPES['url'])
    url_google = Column(TABLE_TYPES['url'])
    url_tweeter = Column(TABLE_TYPES['url'])
    url_linkedin = Column(TABLE_TYPES['url'])
    # url_vkontakte = Column(TABLE_TYPES['url'])

    company_owner_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), unique=True)
    # portal_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal_plan.id'))
    portal_layout_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_layout.id'))

    # logo_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    logo_file_img = relationship(FileImg, uselist=False)
    logo = FileImgDescriptor(relation_name='logo_file_img',
                             file_decorator=lambda p, r, f: f.attr(
                                 name='%s_for_portal_logo_%s' % (f.name, p.id),
                                 parent_id=p.own_company.system_folder_file_id,
                                 root_folder_id=p.own_company.system_folder_file_id),
                             image_size=[480, 480],
                             min_size=[100, 100],
                             aspect_ratio=[0.25, 4.],
                             no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_company_logo()))

    favicon_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))

    layout = relationship('PortalLayout')

    advs = relationship('PortalAdvertisment', uselist=True)

    tags = relationship(Tag, uselist=True, cascade="all, delete-orphan")

    divisions = relationship('PortalDivision',
                             # backref='portal',
                             order_by='desc(PortalDivision.position)',
                             primaryjoin='Portal.id==PortalDivision.portal_id')
    config = relationship('PortalConfig', back_populates='portal', uselist=False)

    divisions_lazy_dynamic = relationship('PortalDivision',
                                          order_by='desc(PortalDivision.position)',
                                          primaryjoin='Portal.id==PortalDivision.portal_id',
                                          lazy='dynamic')

    own_company = relationship('Company',
                               # back_populates='own_portal',
                               uselist=False)
    # articles = relationship('ArticlePortalDivision',
    #                         back_populates='portal',
    #                         uselist=False)
    publications = relationship('Publication',
                                secondary='portal_division',
                                primaryjoin="Portal.id == PortalDivision.portal_id",
                                secondaryjoin="PortalDivision.id == Publication.portal_division_id",
                                back_populates='portal',
                                uselist=False)

    company_members = relationship('MemberCompanyPortal',
                                   # secondary='member_company_portal'
                                   # back_populates='portal',
                                   # lazy='dynamic'
                                   )
    # search_fields = {'name': {'relevance': lambda field='name': RELEVANCE.name},
    #                  'host': {'relevance': lambda field='host': RELEVANCE.host}}

    ALLOWED_STATUSES_TO_JOIN = {
        'DELETED': 'DELETED',
        'REJECTED': 'REJECTED'
    }

    def __init__(self, name=None,
                 # portal_plan_id=None,
                 company_owner=None,
                 favicon_file_id=None,
                 lang='uk',
                 host=None, divisions=[], portal_layout_id=None):
        self.name = name
        self.lang = lang

        self.favicon_file_id = favicon_file_id

        self.host = host
        self.divisions = divisions
        self.portal_layout_id = portal_layout_id if portal_layout_id else db(PortalLayout).first().id

        self.own_company = company_owner

        self.company_members = [
            MemberCompanyPortal(portal=self, company=company_owner, status=MemberCompanyPortal.STATUSES['ACTIVE'],
                                plan=db(MemberCompanyPortalPlan).first())]

    def setup_created_portal(self, client_data):
        # TODO: OZ by OZ: move this to some event maybe
        """This method create portal in db. Before define this method you have to create
        instance of class with parameters: name, host, portal_layout_id, company_owner_id,
        divisions. Return portal)"""

        for division in self.divisions:
            if division.portal_division_type_id == 'company_subportal':
                PortalDivisionSettingsCompanySubportal(
                    member_company_portal=division.settings['member_company_portal'],
                    portal_division=division).save()

        self.logo = client_data['logo']

        # if logo_file_id:
        #     originalfile = File.get(logo_file_id)
        #     if originalfile:
        #         self.logo_file_id = originalfile.copy_file(
        #             company_id=self.company_owner_id,
        #             parent_folder_id=self.own_company.system_folder_file_id,
        #             publication_id=None).save().id
        return self

    # def fallback_default_value(self, key=None, division_name=None):
    #
    #     return default

    # TODO: OZ by OZ fix this
    def get_value_from_config(self, key=None, division_name=None, default=None):
        return default

        """
        :param key: string, variable which you want to return from config
        optional:
            :param division_name: string, if provided return value from config for division this.
        :return: variable which you want to return from config
        """
        conf = getattr(self.config, key, None)
        if not conf:
            return Config.ITEMS_PER_PAGE
        values = simplejson.loads(conf)
        if division_name:
            ret = values.get(division_name)
        else:
            ret = values
        return ret

    def validate_tags(self, new_portal_tags):
        ret = PRBase.DEFAULT_VALIDATION_ANSWER()
        unique = {}
        for tag_id, tag in new_portal_tags.items():
            if not re.match(r'[^\s]{3}', tag['text']):
                if not 'tags' in ret['errors']:
                    ret['errors']['tags'] = {}
                ret['errors']['tags'][tag_id] = 'Pls enter correct tag name'
            if tag['text'] in unique:
                if not 'tags' in ret['errors']:
                    ret['errors']['tags'] = {}
                ret['errors']['tags'][tag_id] = 'Tag names should be unique'
                ret['errors']['tags'][unique[tag['text']]] = 'Tag names should be unique'
            unique[tag['text']] = tag_id
        return ret

    def set_tags(self, new_portal_tags, new_division_tags_matrix):
        tags_to_remove = []
        for existing_tag_portal in self.tags:
            if existing_tag_portal.id in new_portal_tags:
                existing_tag_portal.text = new_portal_tags[existing_tag_portal.id]['text']
                existing_tag_portal.description = new_portal_tags[existing_tag_portal.id]['description']

                for djson in new_division_tags_matrix:
                    division = next(d for d in self.divisions if d.id == djson['id'])
                    tag_is_allowed_for_division = next((tag_in_div for tag_in_div in division.tags
                                                        if tag_in_div.id == existing_tag_portal.id), None)
                    tag_should_be_allowed_for_division = djson['tags'].get(existing_tag_portal.id)

                    if (tag_is_allowed_for_division and not tag_should_be_allowed_for_division):
                        division.tags.remove(tag_is_allowed_for_division)
                    elif (not tag_is_allowed_for_division and tag_should_be_allowed_for_division):
                        division.tags.append(existing_tag_portal)

                del new_portal_tags[existing_tag_portal.id]
            else:
                tags_to_remove.append(existing_tag_portal)

        for remove_tag in tags_to_remove:
            self.tags.remove(remove_tag)

        for add_tag_id, add_tag in new_portal_tags.items():
            new_tag = Tag(portal=self, text=add_tag['text'], description=add_tag['description'])
            self.tags.append(new_tag)
            for djson in new_division_tags_matrix:
                division = next(d for d in self.divisions if d.id == djson['id'])
                if djson['tags'].get(add_tag_id):
                    division.tags.append(new_tag)

        return self

    def validate(self, is_new):
        ret = super().validate(is_new)
        if db(Portal, company_owner_id=self.own_company.id).filter(Portal.id != self.id).count():
            ret['errors']['form'] = 'portal for company already exists'
        if not re.match('[^\s]{3,}', self.name):
            ret['errors']['name'] = 'pls enter a bit longer name'
        if not re.match(
                '^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9]{1,})$',
                self.host):
            ret['errors']['host'] = 'pls enter valid host name'
        if not 'host' in ret['errors'] and db(Portal, host=self.host).filter(Portal.id != self.id).count():
            ret['errors']['host'] = 'host already taken by another portal'

        if not 'host' in ret['errors']:
            import socket

            try:
                host = socket.gethostbyname(self.host)
                host_ip = str(host)
                if not 'host' in ret['errors'] and 'host' in ret['warnings'] and not host_ip in ['136.243.204.62']:
                    ret['warnings']['host'] = 'Wrong Ip-address'
            except Exception as e:
                ret['warnings']['host'] = 'cannot resolve hostname. maybe unregistered'

        grouped = {'by_company_member': {}, 'by_division_type': {}}

        for inddiv, div in enumerate(self.divisions):
            if not re.match('[^\s]{3,}', div.name):
                if not 'divisions' in ret['errors']:
                    ret['errors']['divisions'] = {}
                ret['errors']['divisions'][inddiv] = 'pls enter valid name'

            # number of division of some type
            if div.portal_division_type_id in grouped['by_division_type']:
                grouped['by_division_type'][div.portal_division_type_id] += 1
            else:
                grouped['by_division_type'][div.portal_division_type_id] = 1

            if div.portal_division_type_id == 'company_subportal':
                member_company_id = div.settings['member_company_portal'].company_id
                if member_company_id in grouped['by_company_member']:
                    grouped['by_company_member'][member_company_id] += 1
                else:
                    grouped['by_company_member'][member_company_id] = 1

        for check_division in db(PortalDivisionType).all():
            if check_division.id not in grouped['by_division_type']:
                grouped['by_division_type'][check_division.id] = 0
            if check_division.min > grouped['by_division_type'][check_division.id]:
                ret['errors']['add_division'] = 'you need at least %s `%s`' % (check_division.min, check_division.id)
                if grouped['by_division_type'][check_division.id] == 0:
                    ret['errors']['add_division'] = 'add at least one `%s`' % (check_division.id,)
            if check_division.max < grouped['by_division_type'][check_division.id]:
                for inddiv, div in enumerate(self.divisions):
                    if div.portal_division_type_id == check_division.id:
                        if not 'remove_division' in ret['errors']:
                            ret['errors']['remove_division'] = {}
                        ret['errors']['remove_division'][inddiv] = 'you can have only %s `%s`' % (check_division.max,
                                                                                                  check_division.id)

        for inddiv, div in enumerate(self.divisions):
            if div.portal_division_type_id == 'company_subportal':
                if div.settings['member_company_portal'].company_id in grouped['by_company_member'] and grouped[
                    'by_company_member'][div.settings['member_company_portal'].company_id] > 1:
                    if not 'remove_division' in ret['warnings']:
                        ret['warnings']['remove_division'] = {}
                    ret['warnings']['remove_division'][inddiv] = 'you have more that one subportal for this company'

        return ret

    def get_client_side_dict(self,
                             fields='id|name|host|tags, divisions.*, divisions.tags.*, layout.*, logo.url, '
                                    'favicon_file_id, '
                                    'company_owner_id, url_facebook',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def search_for_portal_to_join(company_id, searchtext):
        """This method return all portals which are not partners current company"""
        portals = []
        for portal in db(Portal).filter(Portal.name.ilike("%" + searchtext + "%")).all():
            member = db(MemberCompanyPortal, company_id=company_id, portal_id=portal.id).first()
            if member and member.status in Portal.ALLOWED_STATUSES_TO_JOIN:
                portals.append(portal.get_client_side_dict())
            elif not member:
                portals.append(portal.get_client_side_dict())
        return portals

    def subscribe_user(self, user = None):
        user = user if user else g.user
        free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
                               ReaderUserPortalPlan.amount).filter_by(name='free').one()

        start_tm = datetime.datetime.utcnow()
        end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp() + free_plan[1])
        reader_portal = UserPortalReader(user.id, self.id, status='active', portal_plan_id=free_plan[0],
                                         start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
                                         show_divisions_and_comments=[division_show for division_show in
                                                                      [ReaderDivision(portal_division=division)
                                                                       for division in self.divisions]])
        g.db.add(reader_portal)
        g.db.commit()


class PortalAdvertisment(Base, PRBase):
    __tablename__ = 'portal_adv'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    place = Column(TABLE_TYPES['short_text'], nullable=False)
    html = Column(TABLE_TYPES['text'], nullable=False)
    portal = relationship(Portal, uselist=False)

    def __init__(self, portal_id=None, place=None, html=None):
        self.portal_id = portal_id
        self.place = place
        self.html = html

    def get_portal_advertisments(self, portal_id=None, filters=None):
        return db(PortalAdvertisment, portal_id=portal_id).order_by(PortalAdvertisment.place)

    def get_client_side_dict(self, fields='id,portal_id,place,html', more_fields=None):
        return self.to_dict(fields, more_fields)


class MemberCompanyPortal(Base, PRBase, PRElasticDocument):
    __tablename__ = 'member_company_portal'

    class RIGHT_AT_PORTAL(BinaryRights):
        PUBLICATION_PUBLISH = 1
        PUBLICATION_UNPUBLISH = 2

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    rights = Column(TABLE_TYPES['binary_rights'](RIGHT_AT_PORTAL),
                    default={RIGHT_AT_PORTAL.PUBLICATION_PUBLISH: True},
                    nullable=False)

    tags = relationship(Tag, secondary='tag_membership')

    member_company_portal_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal_plan.id'))

    status = Column(TABLE_TYPES['status'], default='APPLICANT', nullable=False)

    portal = relationship(Portal)

    company = relationship('Company')

    plan = relationship('MemberCompanyPortalPlan')

    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE',
                'SUSPENDED': 'SUSPENDED', 'FROZEN': 'FROZEN', 'DELETED': 'DELETED'}

    def get_client_side_dict(self, fields='id,status,rights,portal_id,company_id,tags', more_fields=None):
        return self.to_dict(fields, more_fields)

    # elasticsearch begin
    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),
            'tags': PRElasticField(analyzed=False, setter=lambda: ' '.join([t.text for t in self.tags]), boost=5),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),
            'status': PRElasticField(setter=lambda: self.status, analyzed=False),
            'company_name': PRElasticField(setter=lambda: self.company.name, boost=100),
            'company_about': PRElasticField(setter=lambda: self.strip_tags(self.company.about), boost=10),
            'company_short_description': PRElasticField(setter=lambda: self.strip_tags(self.company.short_description), boost=10),
            'company_city': PRElasticField(setter=lambda: self.company.city, boost=2),
            'company_id': PRElasticField(setter=lambda: self.company.id, analyzed=False),
            'portal': PRElasticField(setter=lambda: self.portal.name),
            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.portal.id)
        }

    def elastic_get_index(self):
        return 'company_membership'

    def elastic_get_doctype(self):
        return 'company_membership'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def is_active(self):
        if self.status != MemberCompanyPortal.STATUSES['ACTIVE']:
            return False
        return True

    def __init__(self, company_id=None, portal=None, company=None, plan=None, status=None):
        if company_id and company:
            raise BadDataProvided
        if company_id:
            self.company_id = company_id
        else:
            self.company = company
        self.portal = portal
        self.plan = plan
        self.status = status

    @staticmethod
    def apply_company_to_portal(company_id, portal_id):
        """Add company to MemberCompanyPortal table. Company will be partner of this portal"""
        member = db(MemberCompanyPortal).filter_by(portal_id=portal_id, company_id=company_id).first()
        if member:
            member.set_client_side_dict(MemberCompanyPortal.STATUSES['APPLICANT'])
            member.save()
        else:
            g.db.add(MemberCompanyPortal(company_id=company_id,
                                         portal=db(Portal, id=portal_id).one(),
                                         plan=db(MemberCompanyPortalPlan).first()))
            g.db.flush()

    @staticmethod
    def get_by_portal_id_company_id(portal_id=None, company_id=None):
        return db(MemberCompanyPortal).filter_by(portal_id=portal_id, company_id=company_id).first()

    @staticmethod
    def get_members(company_id, *args):
        subquery = db(MemberCompanyPortal).filter(
            MemberCompanyPortal.portal_id == db(Portal, company_owner_id=company_id).subquery().c.id).filter(
            MemberCompanyPortal.status != MemberCompanyPortal.STATUSES['REJECTED'])
        return subquery

    def set_client_side_dict(self, status=None, rights=None):
        if status:
            self.status = status
        if rights:
            self.rights = rights

    def has_rights(self, rightname):
        if self.portal.own_company.id == self.company_id:
            return True

        if rightname == '_OWNER':
            return False

        if rightname == '_ANY':
            return True if self.status == MemberCompanyPortal.STATUSES['ACTIVE'] else False
        return True if (self.status == MemberCompanyPortal.STATUSES['ACTIVE'] and self.rights[rightname]) else False

    def set_tags_positions(self):
        tag_position = 0
        for tag in self.tags:
            tag_position += 1
            tag_pub = db(TagMembership).filter(and_(TagMembership.tag_id == tag.id,
                                                    TagMembership.member_company_portal_id == self.id)).one()
            tag_pub.position = tag_position
            tag_pub.save()
        return self


class ReaderUserPortalPlan(Base, PRBase):
    __tablename__ = 'reader_user_portal_plan'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['name'], nullable=False, default='free')
    time = Column(TABLE_TYPES['bigint'], default=9999999)
    price = Column(TABLE_TYPES['float'], default=0)
    amount = Column(TABLE_TYPES['int'], default=9999999)

    def __init__(self, name=None, time=None, price=None, amount=None):
        super(ReaderUserPortalPlan, self).__init__()
        self.name = name
        self.time = time
        self.price = price
        self.amount = amount


class PortalLayout(Base, PRBase):
    __tablename__ = 'portal_layout'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['name'], nullable=False)
    path = Column(TABLE_TYPES['name'], nullable=False)

    def __init__(self, name=None):
        self.name = name

    def get_client_side_dict(self, fields='id|name',
                             more_fields=None):
        return self.to_dict(fields, more_fields)


class MemberCompanyPortalPlan(Base, PRBase):
    __tablename__ = 'member_company_portal_plan'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['short_name'], default='')


class PortalDivision(Base, PRBase):
    __tablename__ = 'portal_division'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    portal_division_type_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division_type.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    name = Column(TABLE_TYPES['short_name'], default='')
    position = Column(TABLE_TYPES['int'])

    portal = relationship(Portal, uselist=False)
    portal_division_type = relationship('PortalDivisionType', uselist=False)

    tags = relationship(Tag, secondary='tag_portal_division', uselist=True
                        # ,foreign_keys=[TagPortalDivision.tag_portal_id]
                        )

    # secondary = 'portal_division',
    # primaryjoin = "Portal.id == PortalDivision.portal_id",
    # secondaryjoin = "PortalDivision.id == ArticlePortalDivision.portal_division_id",

    settings = None

    TYPES = {'company_subportal': 'company_subportal', 'index': 'index', 'news': 'news', 'events': 'events',
             'catalog': 'catalog'}

    def is_active(self):
        return True

    def __init__(self, portal=portal,
                 portal_division_type_id=portal_division_type_id,
                 name='',
                 settings=None,
                 position=0):
        self.position = position
        self.portal = portal
        self.portal_division_type_id = portal_division_type_id
        self.name = name
        self.settings = settings

        # @staticmethod
        # def after_attach(session, target):
        #     #     pass
        #     if target.portal_division_type_id == 'company_subportal':
        #         # member_company_portal = db(MemberCompanyPortal, company_id = target.settings['company_id'], portal_id = target.portal_id).one()
        #         addsettings = PortalDivisionSettingsCompanySubportal(
        #             member_company_portal=target.settings.member_company_portal, portal_division=target)
        #         g.db.add(addsettings)
        #         # target.settings = db(PortalDivisionSettingsCompanySubportal).filter_by(
        #         #     portal_division_id=self.id).one()

    # TODO: VK by OZ: do we need this func? i have cemented it becouse IDE shows error here
    # def search_filter(self):
    #     from .articles import ArticlePortalDivision
    #
    #     return and_(ArticlePortalDivision.portal_division_id.in_(
    #             db(PortalDivision.id, portal_id=portal.id)),
    #             ArticlePortalDivision.status ==
    #             ArticlePortalDivision.STATUSES['PUBLISHED'])

    @orm.reconstructor
    def init_on_load(self):
        if self.portal_division_type_id == 'company_subportal':
            self.settings = db(PortalDivisionSettingsCompanySubportal).filter_by(
                portal_division_id=self.id).one()

    def get_client_side_dict(self, fields='id|name|portal_division_type_id|tags',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

        # @staticmethod
        # def add_new_division(portal_id, name, division_type):
        #     """Add new division to current portal"""
        #     return PortalDivision(portal_id=portal_id,
        #                           name=name,
        #                           portal_division_type_id=division_type)


# @event.listens_for(g.db, 'after_attach')
# event.listen(PortalDivision, 'after_attach', PortalDivision.after_attach)


class PortalDivisionSettingsCompanySubportal(Base, PRBase):
    __tablename__ = 'portal_division_settings_company_subportal'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    member_company_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal.id'))

    member_company_portal = relationship(MemberCompanyPortal)

    portal_division = relationship(PortalDivision)

    def __init__(self, member_company_portal=member_company_portal, portal_division=portal_division):
        super(PortalDivisionSettingsCompanySubportal, self).__init__()
        self.portal_division = portal_division
        self.member_company_portal = member_company_portal


class PortalDivisionType(Base, PRBase):
    __tablename__ = 'portal_division_type'
    id = Column(TABLE_TYPES['short_name'], primary_key=True)
    min = Column(TABLE_TYPES['int'])
    max = Column(TABLE_TYPES['int'])

    @staticmethod
    def get_division_types():
        """Return all divisions on profireader"""
        return db(PortalDivisionType).all()


class PortalConfig(Base, PRBase):
    __tablename__ = 'portal_config'
    id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'), primary_key=True)
    division_page_size = Column(TABLE_TYPES['credentials'])
    portal = relationship(Portal, back_populates='config', uselist=False)

    def __init__(self, page_size_for_divisions=None, portal=None):
        """
        optional:
            :parameter - page_size_for_divisions = dictionary with key = division name
                                                             and value = page size per this division
                       , default = all divisions have page size from global config. It will converts
                         to json.
        """
        super(PortalConfig, self).__init__()
        self.portal = portal
        self.page_size_for_divisions = page_size_for_divisions
        self.set_division_page_size()

    PAGE_SIZE_PER_DIVISION = 'division_page_size'

    def set_division_page_size(self, page_size_for_divisions=None):
        page_size_for_divisions = page_size_for_divisions or self.page_size_for_divisions
        config = db(PortalConfig, id=self.id).first()
        dps = dict()
        if config and page_size_for_divisions:
            dps = simplejson.loads(getattr(config, PortalConfig.PAGE_SIZE_PER_DIVISION))
            dps.update(page_size_for_divisions)
        elif page_size_for_divisions:
            for division in self.portal.divisions:
                if page_size_for_divisions.get(division.name):
                    dps[division.name] = page_size_for_divisions.get(division.name)
                else:
                    dps[division.name] = Config.ITEMS_PER_PAGE
        else:
            for division in self.portal.divisions:
                dps[division.name] = Config.ITEMS_PER_PAGE
        dps = simplejson.dumps(dps)
        self.division_page_size = dps


class UserPortalReader(Base, PRBase):
    __tablename__ = 'reader_portal'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    # TODO: VK by OZ: status should be of enum type
    status = Column(TABLE_TYPES['id_profireader'], default='active', nullable=False)
    portal_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('reader_user_portal_plan.id'))
    start_tm = Column(TABLE_TYPES['timestamp'])
    end_tm = Column(TABLE_TYPES['timestamp'])
    amount = Column(TABLE_TYPES['int'], default=99999)
    portal = relationship('Portal', uselist=False)
    user = relationship('User')
    show_divisions_and_comments = relationship('ReaderDivision', back_populates='reader_portal')

    def __init__(self, user_id=None, portal_id=None, status='active', portal_plan_id=None, start_tm=None,
                 end_tm=None, amount=None, show_divisions_and_comments=None):
        super(UserPortalReader, self).__init__()
        self.user_id = user_id
        self.portal_id = portal_id
        self.status = status
        self.start_tm = start_tm
        self.end_tm = end_tm
        self.amount = amount
        self.show_divisions_and_comments = show_divisions_and_comments
        self.portal_plan_id = portal_plan_id or g.db(ReaderUserPortalPlan.id).filter_by(name='free').one()[0]

    def get_portal_divisions_json(self):
        return json.dumps({division[0]: {'name': division[1], 'show_division': True, 'comments': True}
                           for division in db(PortalDivision.id, PortalDivision.name, portal_id=self.portal_id).all()},
                          ensure_ascii=False)

    @staticmethod
    def get_portals_for_user():
        portals = db(Portal).filter(~(Portal.id.in_(db(UserPortalReader.portal_id, user_id=g.user.id)))).all()
        for portal in portals:
            yield (portal.id, portal.name,)

    @staticmethod
    def get(user_id=None, portal_id=None):
        return db(UserPortalReader).filter_by(user_id=user_id, portal_id=portal_id).first()

    @staticmethod
    def get_portals_and_plan_info_for_user(user_id, page, items_per_page, filter_params):
        from ..controllers.pagination import pagination
        query, pages, page, count = pagination(db(UserPortalReader, user_id=user_id).filter(filter_params),
                                               page=int(page), items_per_page=int(items_per_page))

        for upr in query:
            yield dict(id=upr.id, portal_id=upr.portal_id, status=upr.status, start_tm=upr.start_tm,
                       portal_logo=upr.portal.logo['url'],
                       end_tm=upr.end_tm if upr.end_tm > datetime.datetime.utcnow() else 'Expired at ' + upr.end_tm,
                       plan_id=upr.portal_plan_id,
                       plan_name=db(ReaderUserPortalPlan.name, id=upr.portal_plan_id).one()[0],
                       portal_name=upr.portal.name, portal_host=upr.portal.host, amount=upr.amount,
                       portal_divisions=[{division.name: division.id}
                                         for division in upr.portal.divisions])

    @staticmethod
    def get_filter_for_portals_and_plans(portal_name=None, start_end_tm=None, package_name=None):
        filter_params = []
        if portal_name:
            filter_params.append(UserPortalReader.portal_id.in_(db(Portal.id).filter(
                Portal.name.ilike('%' + portal_name + '%'))))
        if start_end_tm:
            from_tm = datetime.datetime.utcfromtimestamp(int(start_end_tm['from'] + 1) / 1000)
            to_tm = datetime.datetime.utcfromtimestamp(int(start_end_tm['to'] + 86399999) / 1000)
            filter_params.extend([UserPortalReader.start_tm >= from_tm,
                                  UserPortalReader.start_tm <= to_tm])
        if package_name:
            filter_params.append(UserPortalReader.portal_plan_id == db(ReaderUserPortalPlan.id).filter(
                ReaderUserPortalPlan.name.ilike('%' + package_name + '%')))
        return filter_params


class ReaderDivision(Base, PRBase):
    __tablename__ = 'reader_division'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False, unique=True)
    reader_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('reader_portal.id'))
    division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    _show_division_and_comments = Column(TABLE_TYPES['int'])
    reader_portal = relationship('UserPortalReader', back_populates='show_divisions_and_comments')
    portal_division = relationship('PortalDivision', uselist=False)
    show_division_and_comments_numeric = {name: 2 ** index for index, name in
                                          enumerate(['show_articles', 'show_comments', 'show_favorite_comments',
                                                     'show_liked_comments'])}
    show_division_and_comments_numeric_all = reduce(lambda x, y: x + y, show_division_and_comments_numeric.values())

    def __init__(self, reader_portal=None, portal_division=None):
        super(ReaderDivision, self).__init__()
        self._show_division_and_comments = self.show_division_and_comments_numeric_all
        self.reader_portal = reader_portal
        self.portal_division = portal_division

    @property
    def show_divisions_and_comments(self):
        return [[sn, True if self._show_division_and_comments & 2 ** ind else False] for ind, sn in
                enumerate(['show_articles', 'show_comments', 'show_favorite_comments', 'show_liked_comments'])]

    @show_divisions_and_comments.setter
    def show_divisions_and_comments(self, tuple_or_list):
        """ :param tuple_or_list, first param from 'show_divisions_and_comments_numeric',
        second True or False """
        self._show_division_and_comments = self.show_division_and_comments_numeric_all & reduce(
            lambda x, y: int(x) + int(y), list(map(lambda item: self.show_division_and_comments_numeric[item[0]],
                                                   filter(lambda item: item[1], tuple_or_list))), 0)
