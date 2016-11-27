from ..constants.TABLE_TYPES import TABLE_TYPES, BinaryRights
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from flask import g
from tools.db_utils import db
from .pr_base import PRBase, Base
import re
from ..constants.SEARCH import RELEVANCE
from sqlalchemy import orm
from config import Config
import simplejson
from .files import File, FileImg, FileImgDescriptor
from ..constants.RECORD_IDS import FOLDER_AND_FILE
from .. import utils
from ..models.tag import Tag, TagMembership
from profapp.controllers.errors import BadDataProvided
import datetime
import json
from functools import reduce
from sqlalchemy.sql import and_
from .elastic import PRElasticField, PRElasticDocument
from sqlalchemy.sql import or_, and_, expression


class Portal(Base, PRBase):
    __tablename__ = 'portal'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['name'])
    host = Column(TABLE_TYPES['short_name'], default='')
    lang = Column(TABLE_TYPES['short_name'])

    status = Column(TABLE_TYPES['status'], default='ACTIVE')
    aliases = Column(TABLE_TYPES['text'], default='')

    url_facebook = Column(TABLE_TYPES['url'])
    url_google = Column(TABLE_TYPES['url'])
    url_twitter = Column(TABLE_TYPES['url'])
    url_linkedin = Column(TABLE_TYPES['url'])
    # url_vkontakte = Column(TABLE_TYPES['url'])


    company_owner_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), unique=True)
    # portal_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal_plan.id'))
    portal_layout_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_layout.id'))

    # logo_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    logo_file_img = relationship(FileImg, uselist=False, foreign_keys=[logo_file_img_id])
    logo = FileImgDescriptor(relation_name='logo_file_img',
                             file_decorator=lambda p, r, f: f.attr(
                                 name='%s_for_portal_logo_%s' % (f.name, p.id),
                                 parent_id=p.own_company.system_folder_file_id,
                                 root_folder_id=p.own_company.system_folder_file_id),
                             image_size=[480, 480],
                             min_size=[100, 100],
                             aspect_ratio=[0.25, 4.],
                             no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_company_logo()))

    # favicon_from = Column(TABLE_TYPES['string_10'], default='')
    # favicon_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(File.id), nullable=True)

    favicon_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    favicon_file_img = relationship(FileImg, uselist=False, foreign_keys=[favicon_file_img_id])
    favicon = FileImgDescriptor(relation_name='favicon_file_img',
                                file_decorator=lambda p, r, f: f.attr(
                                    name='%s_for_portal_favico_%s' % (f.name, p.id),
                                    parent_id=p.own_company.system_folder_file_id,
                                    root_folder_id=p.own_company.system_folder_file_id),
                                image_size=[64, 64],
                                min_size=[16, 16],
                                aspect_ratio=[1, 1],
                                no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_favicon()))

    layout = relationship('PortalLayout')

    advs = relationship('PortalAdvertisment', uselist=True)

    tags = relationship(Tag, uselist=True, cascade="all, delete-orphan")

    divisions = relationship('PortalDivision',
                             # backref='portal',
                             cascade="all, merge, delete-orphan",
                             order_by='asc(PortalDivision.position)',
                             primaryjoin='Portal.id==PortalDivision.portal_id')

    own_company = relationship('Company',
                               # back_populates='own_portal',
                               uselist=False)
    # articles = relationship('ArticlePortalDivision',
    #                         back_populates='portal',
    #                         uselist=False)
    publications = relationship('Publication',
                                cascade="all, merge",
                                secondary='portal_division',
                                primaryjoin="Portal.id == PortalDivision.portal_id",
                                secondaryjoin="PortalDivision.id == Publication.portal_division_id",
                                # back_populates='portal',
                                uselist=True)

    company_memberships = relationship('MemberCompanyPortal',
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

    def __init__(self, **kwargs):
        super(Portal, self).__init__(**kwargs)
        if not self.portal_layout_id:
            self.portal_layout_id = db(PortalLayout).first().id

    def setup_created_portal(self, client_data):
        # TODO: OZ by OZ: move this to some event maybe
        """This method create portal in db. Before define this method you have to create
        instance of class with parameters: name, host, portal_layout_id, company_owner_id,
        divisions. Return portal)"""

        # for division in self.divisions:
        #     if division.portal_division_type_id == PortalDivision.TYPES['company_subportal']:
        #         PortalDivisionSettingsCompanySubportal(
        #             member_company_portal=division.settings['member_company_portal'],
        #             portal_division=division).save()

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

    # # TODO: OZ by OZ fix this
    # def get_value_from_config(self, key=None, division_name=None, default=None):
    #     return default
    #
    #     """
    #     :param key: string, variable which you want to return from config
    #     optional:
    #         :param division_name: string, if provided return value from config for division this.
    #     :return: variable which you want to return from config
    #     """
    #     conf = getattr(self.config, key, None)
    #     if not conf:
    #         return Config.ITEMS_PER_PAGE
    #     values = simplejson.loads(conf)
    #     if division_name:
    #         ret = values.get(division_name)
    #     else:
    #         ret = values
    #     return ret

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
        ret = super().validate(is_new, regexps={
            'name': '[^\s]{2,}',
            'host': '^(([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])\.)+([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9]{1,})$'})
        errors = ret['errors']
        warnings = ret['warnings']

        if db(Portal, company_owner_id=self.own_company.id).filter(Portal.id != self.id).count():
            errors['form'] = 'portal for company already exists'

        if db(Portal, host=self.host).filter(Portal.id != self.id).count():
            errors['host'] = 'host already taken by another portal'

        import socket
        try:
            host = socket.gethostbyname(self.host)
            host_ip = str(host)
            if not 'host' in errors and 'host' in warnings and not host_ip in Config.OUR_IPS:
                warnings['host'] = 'Wrong Ip-address'
        except Exception as e:
            warnings['host'] = 'cannot resolve hostname. maybe unregistered'

        grouped_by_division_type = {}
        grouped_by_company_member = {}

        for inddiv, div in enumerate(self.divisions):
            if not re.match('[^\s]{3,}', div.name):
                utils.dict_deep_replace('pls enter valid name', errors, 'divisions', div.id, 'name')

            # number of division of some type
            utils.dict_deep_inc(grouped_by_division_type, div.portal_division_type.id)

            if div.portal_division_type.id == PortalDivision.TYPES['company_subportal']:
                utils.dict_deep_inc(grouped_by_company_member, div.settings['company_id'])

        for check_division_type in db(PortalDivisionType).all():
            utils.dict_deep_replace(0, grouped_by_division_type, check_division_type.id, if_not_exists=True)

            if check_division_type.min > grouped_by_division_type[check_division_type.id]:
                errors['add_division'] = 'you need at least %s `%s`' % (check_division_type.min, check_division_type.id)

            if check_division_type.max < grouped_by_division_type[check_division_type.id]:
                for inddiv, div in enumerate(self.divisions):
                    if div.portal_division_type.id == check_division_type.id:
                        utils.dict_deep_replace(
                            'you can have only %s `%s`' % (check_division_type.max, check_division_type.id),
                            errors, 'divisions', div.id, 'type')

        for inddiv, div in enumerate(self.divisions):
            if div.portal_division_type.id == PortalDivision.TYPES['company_subportal']:
                if grouped_by_company_member.get(div.settings['company_id'], 0) > 1:
                    utils.dict_deep_replace('you have more that one subportal for this company',
                                            warnings, 'divisions', div.id, 'settings')

        return ret

    def get_client_side_dict(self,
                             fields='id|name|host|tags, divisions.*, divisions.tags.*, layout.*, logo.url, '
                                    'favicon.url, company_owner_id, url_facebook, url_google, url_twitter, url_linkedin',
                             more_fields=None, get_own_or_profi_host=False, get_publications_count=False):
        if get_publications_count:
            more_fields = more_fields + ', divisions.id' if more_fields else 'divisions.id'
        ret = self.to_dict(fields, more_fields)
        if get_publications_count:
            for d in self.divisions:
                if d.portal_division_type.id in [PortalDivision.TYPES['events'], PortalDivision.TYPES['news']]:
                    utils.find_by_id(ret['divisions'], d.id)['publication_count'] = len(d.publications)

        if get_own_or_profi_host:
            if ret['host'][
               len(ret['host']) - len(Config.MAIN_DOMAIN) - 1:] == '.' + Config.MAIN_DOMAIN:
                ret['host_profi_or_own'] = 'profi'
                ret['host_profi'] = ret['host'][
                                    0:len(ret['host']) - len(Config.MAIN_DOMAIN) - 1]
                ret['host_own'] = ''
            else:
                ret['host_profi_or_own'] = 'own'
                ret['host_own'] = ret['host']
                ret['host_profi'] = ''
        return ret

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

    def subscribe_user(self, user=None):
        user = user if user else g.user

        if db(UserPortalReader, portal_id=self.id, user_id=user.id).first():
            return

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

        # # TODO: OZ by OZ: remove this endpoint!!! move subscription to model (function Portal.subscribe_user(self, user))
        # user_dict = g.user.get_client_side_dict()
        # portal = Portal.get(portal_id)
        # if not portal:
        #     raise BadDataProvided
        # reader_portal = g.db.query(UserPortalReader).filter_by(user_id=user_dict['id'], portal_id=portal_id).count()
        # if not reader_portal:
        #     free_plan = g.db.query(ReaderUserPortalPlan.id, ReaderUserPortalPlan.time,
        #                            ReaderUserPortalPlan.amount).filter_by(name='free').one()
        #     start_tm = datetime.datetime.utcnow()
        #     end_tm = datetime.datetime.fromtimestamp(start_tm.timestamp() + free_plan[1])
        #     reader_portal = UserPortalReader(user_dict['id'], portal_id, status='active', portal_plan_id=free_plan[0],
        #                                      start_tm=start_tm, end_tm=end_tm, amount=free_plan[2],
        #                                      show_divisions_and_comments=[division_show for division_show in
        #                                                                   [ReaderDivision(portal_division=division)
        #                                                                    for division in portal.divisions]])
        #     g.db.add(reader_portal)
        #     g.db.commit()
        #     # TODO: OZ by OZ: remove it
        #     from flask import flash
        #     flash('You have successfully subscribed to this portal')


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


class PortalAdvertismentPlace(Base, PRBase):
    __tablename__ = 'portal_layout_adv_places'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    portal_layout_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(PortalLayout.id))
    place = Column(TABLE_TYPES['short_text'], nullable=False)
    help = Column(TABLE_TYPES['text'])
    default_value = Column(TABLE_TYPES['text'])

    portal_layout = relationship(PortalLayout, uselist=False)


class PortalAdvertisment(Base, PRBase):
    __tablename__ = 'portal_adv'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    place = Column(TABLE_TYPES['short_text'], nullable=False)
    html = Column(TABLE_TYPES['text'], nullable=False)
    portal = relationship(Portal, uselist=False)

    @staticmethod
    def get_portal_advertisments(portal):
        places = {p.place: p.get_client_side_dict('help,default_value') for p in
                  db(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id).all()}
        banners = db(PortalAdvertisment, portal_id=portal.id).order_by(PortalAdvertisment.place).all()
        ret = []
        for b in banners:
            if b.place in places:
                ret.append(
                    utils.dict_merge(b.get_client_side_dict(), places[b.place], {'actions': {'set_default': True}}))
                places[b.place] = False
            else:
                ret.append(utils.dict_merge(b.get_client_side_dict(), {'actions': {'delete': True}}))

        for p_name in places:
            if places[p_name] is not False:
                ret.append(utils.dict_merge(
                    {'id': '', 'portal_id': portal.id, 'place': p_name, 'html': '', 'actions': {'create': True}},
                    places[p_name]))
        return ret

    def get_client_side_dict(self, fields='id,portal_id,place,html', more_fields=None):
        return self.to_dict(fields, more_fields)


class MemberCompanyPortal(Base, PRBase, PRElasticDocument):
    __tablename__ = 'member_company_portal'

    class RIGHT_AT_PORTAL(BinaryRights):
        PUBLICATION_PUBLISH = 1
        PUBLICATION_UNPUBLISH = 2

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    rights = Column(TABLE_TYPES['binary_rights'](RIGHT_AT_PORTAL),
                    default={RIGHT_AT_PORTAL.PUBLICATION_PUBLISH: True},
                    nullable=False)

    # tags = relationship(Tag, secondary='tag_membership', foreign_keys = [portal_id, ])
    tags = relationship(Tag, secondary='tag_membership', uselist=True,

                        order_by=lambda: expression.desc(TagMembership.position))

    member_company_portal_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal_plan.id'))

    status = Column(TABLE_TYPES['status'], default='APPLICANT', nullable=False)

    portal = relationship(Portal)

    company = relationship('Company')

    plan = relationship('MemberCompanyPortalPlan')

    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE',
                'SUSPENDED': 'SUSPENDED', 'FROZEN': 'FROZEN', 'DELETED': 'DELETED'}

    def get_client_side_dict(self, fields='id,status,rights,portal_id,company_id,tags', more_fields=None):
        return self.to_dict(fields, more_fields)

    def seo_dict(self):
        return {
            'title': self.company.name,
            'keywords': ','.join(t.text for t in self.tags),
            'description': self.company.short_description if self.company.short_description else self.company.about,
            'image_url': self.company.logo['url'] if self.company.logo['selected_by_user']['type'] == 'provenance' else None
        }

    # elasticsearch begin
    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),

            'tags': PRElasticField(setter=lambda: ' '.join([t.text for t in self.tags])),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),

            'status': PRElasticField(setter=lambda: self.status, analyzed=False),

            'company_id': PRElasticField(analyzed=False, setter=lambda: self.company.id),
            'company_name': PRElasticField(setter=lambda: self.company.name),

            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.portal.id),
            'portal_name': PRElasticField(setter=lambda: self.portal.name),

            'division_id': PRElasticField(analyzed=False, setter=lambda: db(PortalDivision, portal_id=self.portal.id,
                                                                            portal_division_type_id='catalog').one().id),
            'division_type': PRElasticField(analyzed=False, setter=lambda: 'catalog'),
            'division_name': PRElasticField(setter=lambda: self.portal.name),

            'date': PRElasticField(ftype='date',
                                   setter=lambda: int(self.cr_tm.timestamp() * 1000) if self.cr_tm else 0),

            'title': PRElasticField(setter=lambda: self.company.name, boost=10),
            'subtitle': PRElasticField(setter=lambda: self.strip_tags(self.company.about), boost=5),
            'keywords': PRElasticField(setter=lambda: '', boost=5),
            'short': PRElasticField(setter=lambda: self.strip_tags(self.company.short_description), boost=2),

            'long': PRElasticField(setter=lambda: ''),

            'author': PRElasticField(setter=lambda: ''),
            'address': PRElasticField(setter=lambda: ''),

            'custom_data': PRElasticField(analyzed=False, setter=lambda: simplejson.dumps({}))

            # 'company_name': PRElasticField(setter=lambda: self.company.name, boost=100),
            # 'company_about': PRElasticField(setter=lambda: self.strip_tags(self.company.about), boost=10),
            # 'company_short_description': PRElasticField(setter=lambda: self.strip_tags(self.company.short_description),
            #                                             boost=10),
            # 'company_city': PRElasticField(setter=lambda: self.company.city, boost=2),

        }

    def elastic_get_index(self):
        return 'front'

    def elastic_get_doctype(self):
        return 'company'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def elastic_insert(self):
        pass

    def is_active(self):
        if self.status != MemberCompanyPortal.STATUSES['ACTIVE']:
            return False
        return True

    # def __init__(self, company_id=None, portal=None, company=None, plan=None, status=None):
    #     if company_id and company:
    #         raise BadDataProvided
    #     if company_id:
    #         self.company_id = company_id
    #     else:
    #         self.company = company
    #     self.portal = portal
    #     self.plan = plan
    #     self.status = status

    @staticmethod
    def apply_company_to_portal(company_id, portal_id):
        from ..models.company import Company
        """Add company to MemberCompanyPortal table. Company will be partner of this portal"""
        member = db(MemberCompanyPortal).filter_by(portal_id=portal_id, company_id=company_id).first()
        if member:
            member.set_client_side_dict(MemberCompanyPortal.STATUSES['APPLICANT'])
            member.save()
        else:
            g.db.add(MemberCompanyPortal(company=Company.get(company_id),
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


class MemberCompanyPortalPlan(Base, PRBase):
    __tablename__ = 'member_company_portal_plan'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['short_name'], default='')


class PortalDivisionSettingsDescriptor(object):
    def __init__(self):
        pass

    def __get__(self, instance, owner):
        return {
            'id': instance.portal_division_settings_company_subportal.id,
            'company_id': instance.portal_division_settings_company_subportal.member_company_portal.company_id
        } if instance.portal_division_type.id == PortalDivision.TYPES['company_subportal'] else {}

    # def proxy_setter(self, file_img: FileImg, client_data):
    def __set__(self, instance, data):
        if instance.portal_division_type.id == PortalDivision.TYPES['company_subportal']:
            membership = next(cm for cm in instance.portal.company_memberships if cm.company.id == data['company_id'])
            if not instance.portal_division_settings_company_subportal:
                instance.portal_division_settings_company_subportal = \
                    PortalDivisionSettingsCompanySubportal(portal_division=instance, member_company_portal=membership)
            instance.portal_division_settings_company_subportal.member_company_portal.company_id = membership.company.id

        # self.id = client_data.get('id', None)
        # self.company_id = client_data.get('company_id', None)
        # self.member_company_portal_id = client_data.get('member_company_portal_id', None)
        return True


class PortalDivision(Base, PRBase):
    __tablename__ = 'portal_division'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    portal_division_type_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division_type.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))

    name = Column(TABLE_TYPES['short_name'], default='')

    html_description = Column(TABLE_TYPES['string_10000'], default='')
    html_title = Column(TABLE_TYPES['string_1000'], default='')
    html_keywords = Column(TABLE_TYPES['string_1000'], default='')

    position = Column(TABLE_TYPES['int'])

    portal = relationship(Portal, uselist=False)

    portal_division_type = relationship('PortalDivisionType', uselist=False)

    portal_division_settings_company_subportal = relationship('PortalDivisionSettingsCompanySubportal', uselist=False,
                                                              cascade="all, merge, delete-orphan")
    settings = PortalDivisionSettingsDescriptor()

    tags = relationship(Tag, secondary='tag_portal_division', uselist=True)

    publications = relationship('Publication', cascade="all, delete-orphan")

    TYPES = {'company_subportal': 'company_subportal', 'index': 'index', 'news': 'news', 'events': 'events',
             'catalog': 'catalog'}

    def seo_dict(self):
        return {
            'title': self.html_title if self.html_title else self.name,
            'keywords': self.html_keywords if self.html_keywords else ','.join(t.text for t in self.tags),
            'description': self.html_description
        }

    def notice_about_deleted_publications(self, because_of):
        from ..models.messenger import Socket, Notification
        from ..models.rights import PublishUnpublishInPortal
        dict_main = {
            'portal_division': self,
            'portal': self.portal
        }

        for p in self.publications:
            dict_pub = utils.dict_merge(dict_main, {
                'publication': p,
                'material': p.material
            })
            phrase = "Because of " + because_of + " user <a href=\"%(url_profile_from_user)s\">%(from_user.full_name)s</a> just complitelly deleted a " \
                                                  "material named `%(material.title)s` from portal <a class=\"external_link\" target=\"blank_\" href=\"//%(portal.host)s\">%(portal.name)s<span class=\"fa fa-external-link pr-external-link\"></span></a>"

            to_users = PublishUnpublishInPortal(p, self, self.portal.own_company).get_user_with_rights(
                PublishUnpublishInPortal.publish_rights)
            if p.material.editor not in to_users:
                to_users.append(p.material.editor)

            # possible notification - 2
            Socket.prepare_notifications(to_users, Notification.NOTIFICATION_TYPES['PUBLICATION_ACTIVITY'], phrase,
                                         dict_pub)()

    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id|portal_division_type_id|tags|settings|name|html_title|html_keywords|html_description',
                             more_fields=None):
        return self.to_dict(fields, more_fields)


class PortalDivisionSettingsCompanySubportal(Base, PRBase):
    __tablename__ = 'portal_division_settings_company_subportal'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    member_company_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal.id'))

    member_company_portal = relationship(MemberCompanyPortal)

    portal_division = relationship(PortalDivision, cascade="all, merge, delete")


class PortalDivisionType(Base, PRBase):
    __tablename__ = 'portal_division_type'
    id = Column(TABLE_TYPES['short_name'], primary_key=True)
    min = Column(TABLE_TYPES['int'])
    max = Column(TABLE_TYPES['int'])

    @staticmethod
    def get_division_types():
        """Return all divisions on profireader"""
        return db(PortalDivisionType).all()


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
