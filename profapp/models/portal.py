import datetime
import json
import re
from functools import reduce

import simplejson
from flask import g, url_for
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_, expression

from config import Config
from .elastic import PRElasticField, PRElasticDocument
from .files import FileImg, FileImgDescriptor
from .pr_base import PRBase, Base
from .. import utils
from ..constants.RECORD_IDS import FOLDER_AND_FILE
from ..constants.TABLE_TYPES import TABLE_TYPES, BinaryRights
from ..models.tag import Tag, TagMembership


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
    portal_layout_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_layout.id'))

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    logo_file_img = relationship(FileImg, uselist=False, foreign_keys=[logo_file_img_id])
    logo = FileImgDescriptor(relation_name='logo_file_img',
                             file_decorator=lambda p, r, f: f.attr(
                                 name='%s_for_portal_logo_%s' % (f.name, p.id),
                                 parent_id=p.own_company.system_folder_file_id,
                                 root_folder_id=p.own_company.system_folder_file_id),
                             image_size=[480, 480],
                             min_size=[100, 100],
                             aspect_ratio=[0.125, 8.],
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

    plans = relationship('MembershipPlan',
                         cascade="all, merge, delete-orphan",
                         order_by='asc(MembershipPlan.position)',
                         primaryjoin='and_(Portal.id == MembershipPlan.portal_id, MembershipPlan.status != \'DELETED\')')

    plans_active = relationship('MembershipPlan',
                                cascade="all, merge, delete-orphan",
                                order_by='asc(MembershipPlan.position)',
                                primaryjoin='and_(Portal.id==MembershipPlan.portal_id, MembershipPlan.status == \'ACTIVE\')')

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

    company_memberships = relationship('MemberCompanyPortal')

    default_membership_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan.id'), nullable=False)
    default_membership_plan = relationship('MembershipPlan', uselist=False, post_update=True,
                                           foreign_keys=[default_membership_plan_id])
    # post_update parameter is for breaking Circular dependency error (which us because mutual dependency exists default_membership_plan <-> plans)
    # http://docs.sqlalchemy.org/en/rel_1_1/orm/relationship_api.html#sqlalchemy.orm.relationship.params.post_update

    # search_fields = {'name': {'relevance': lambda field='name': RELEVANCE.name},
    #                  'host': {'relevance': lambda field='host': RELEVANCE.host}}

    ALLOWED_STATUSES_TO_JOIN = {
        'DELETED': 'DELETED',
        'REJECTED': 'REJECTED'
    }

    def __init__(self, **kwargs):
        super(Portal, self).__init__(**kwargs)
        if not self.portal_layout_id:
            self.portal_layout_id = utils.db.query_filter(PortalLayout).first().id

    @staticmethod
    def launch_new_portal(company):
        # This all ids (by db_utils.create_uuid()) we need because we have mutual foreign keys in database and
        # NOT NULL constrain (and not null constrain don't support deferrable property')

        from tools import db_utils
        ret = Portal(host='', lang=g.user.lang,
                     id=db_utils.create_uuid(),
                     own_company=company,
                     company_owner_id=company.id,
                     default_membership_plan_id=db_utils.create_uuid(),
                     company_memberships=[
                         MemberCompanyPortal(
                             id=db_utils.create_uuid(),
                             company=company,
                             rights={MemberCompanyPortal.RIGHT_AT_PORTAL._OWNER: True},
                             status=MemberCompanyPortal.STATUSES['ACTIVE'])])

        ret.default_membership_plan = MembershipPlan(name='default', position=0,
                                                     portal_id=ret.id,
                                                     status=MembershipPlan.STATUSES['ACTIVE'],
                                                     duration='1 years',
                                                     publication_count_open=-1,
                                                     publication_count_registered=10,
                                                     publication_count_payed=0,
                                                     price=1, currency_id='UAH')

        ret.company_memberships[0].portal = ret
        ret.company_memberships[0].current_membership_plan_issued = ret.company_memberships[0].create_issued_plan()
        ret.company_memberships[0].current_membership_plan_issued.start()

        return ret

        # ret.company_memberships[0].current_membership_plan_issued \
        #     = MembershipPlanIssued.create_for_membership(ret.company_memberships[0], ret.default_membership_plan)
        # ret.company_memberships[0].current_membership_plan_issued. \
        #     member_company_portal_id = ret.company_memberships[0].id

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

        if utils.db.query_filter(Portal, company_owner_id=self.own_company.id).filter(Portal.id != self.id).count():
            errors['form'] = 'portal for company already exists'

        if utils.db.query_filter(Portal, host=self.host).filter(Portal.id != self.id).count():
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

        for check_division_type in utils.db.query_filter(PortalDivisionType).all():
            utils.dict_deep_replace(0, grouped_by_division_type, check_division_type.id, add_only_if_not_exists=True)

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
        for portal in utils.db.query_filter(Portal).filter(Portal.name.ilike("%" + searchtext + "%")).all():
            member = utils.db.query_filter(MemberCompanyPortal, company_id=company_id, portal_id=portal.id).first()
            if member and member.status in Portal.ALLOWED_STATUSES_TO_JOIN:
                portals.append(portal.get_client_side_dict())
            elif not member:
                portals.append(portal.get_client_side_dict())
        return portals

    def subscribe_user(self, user=None):
        user = user if user else g.user

        if utils.db.query_filter(UserPortalReader, portal_id=self.id, user_id=user.id).first():
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
                  utils.db.query_filter(PortalAdvertismentPlace, portal_layout_id=portal.portal_layout_id).all()}
        banners = utils.db.query_filter(PortalAdvertisment, portal_id=portal.id).order_by(
            PortalAdvertisment.place).all()
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


class MembershipPlan(Base, PRBase):
    __tablename__ = 'membership_plan'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    name = Column(TABLE_TYPES['string_100'])

    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Portal.id))
    portal = relationship('Portal', foreign_keys=[portal_id])

    publication_count_open = Column(TABLE_TYPES['int'])
    publication_count_registered = Column(TABLE_TYPES['int'])
    publication_count_payed = Column(TABLE_TYPES['int'])
    publication_count_confidential = Column(TABLE_TYPES['int'])

    price = Column(TABLE_TYPES['price'])
    currency_id = Column(TABLE_TYPES['string_10'])

    duration = Column(TABLE_TYPES['timeinterval'])

    position = Column(TABLE_TYPES['int'])
    status = Column(TABLE_TYPES['string_100'])

    auto_apply = Column(TABLE_TYPES['string_100'], default=False, nullable=False)

    # default = Column(TABLE_TYPES['boolean'])

    STATUSES = {'ACTIVE': 'ACTIVE', 'INACTIVE': 'INACTIVE', 'DELETED': 'DELETED'}

    DURATION_UNITS = [
        {'id': 'days', 'name': 'Days'},
        {'id': 'weeks', 'name': 'Weeks'},
        {'id': 'months', 'name': 'Months'},
        {'id': 'years', 'name': 'Years'},
    ]

    def get_client_side_dict(self,
                             fields='id,name,cr_tm,status,currency_id,price,duration,auto_apply,'
                                    'publication_count_open,publication_count_registered,publication_count_payed',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    def validate(self, is_new=False):
        ret = super().validate(is_new=is_new, regexps={'name': '[^\s]{3,}'})
        return ret


class MembershipPlanIssued(Base, PRBase):
    __tablename__ = 'membership_plan_issued'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    started_tm = Column(TABLE_TYPES['timestamp'])
    started_by_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    started_by_user = relationship('User', foreign_keys=[started_by_user_id])

    name = Column(TABLE_TYPES['short_name'])
    stopped_tm = Column(TABLE_TYPES['timestamp'])
    calculated_stopping_tm = Column(TABLE_TYPES['timestamp'])

    price = Column(TABLE_TYPES['price'])
    currency_id = Column(TABLE_TYPES['string_10'])
    duration = Column(TABLE_TYPES['timeinterval'])
    publication_count_open = Column(TABLE_TYPES['int'])
    publication_count_registered = Column(TABLE_TYPES['int'])
    publication_count_payed = Column(TABLE_TYPES['int'])
    publication_count_confidential = Column(TABLE_TYPES['int'])

    stopped_by_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    stopped_by_user = relationship('User', foreign_keys=[stopped_by_user_id])

    requested_by_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    requested_by_user = relationship('User', foreign_keys=[requested_by_user_id])

    member_company_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal.id'))
    member_company_portal = relationship('MemberCompanyPortal', foreign_keys=[member_company_portal_id])

    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))

    membership_plan_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan.id'))
    membership_plan = relationship(MembershipPlan)

    auto_apply = Column(TABLE_TYPES['boolean'], default=False, nullable=False)
    confirmed = Column(TABLE_TYPES['boolean'], default=False, nullable=False)

    auto_renew = Column(TABLE_TYPES['boolean'], default=True, nullable=False)

    def get_client_side_dict(self,
                             fields='id,name,cr_tm,started_tm,calculated_stopping_tm,stopped_tm,confirmed,'
                                    'currency_id,price,publication_count_open,publication_count_registered,publication_count_payed,duration',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

        # status = Column(TABLE_TYPES['string_100'])

    def start(self, user=None):
        self.started_tm = datetime.datetime.utcnow()
        duration, duration_unit = self.duration.split(' ')
        duration = int(float(duration))
        if duration > 0:
            if duration_unit == 'years':
                self.calculated_stopping_tm = self.started_tm.replace(year=self.started_tm.year + duration)
            elif duration_unit == 'months':
                add_year = duration // 12
                new_month = self.started_tm.month + duration - add_year * 12
                if new_month > 12:
                    add_year += new_month // 12
                    new_month -= (new_month // 12) * 12
                self.calculated_stopping_tm = self.started_tm.replace(year=self.started_tm.year + add_year,
                                                                      month=new_month)
            elif duration_unit == 'weeks':
                self.calculated_stopping_tm = datetime.datetime.fromtimestamp(
                    self.started_tm.timestamp() + duration * 7 * 24 * 3600)
            elif duration_unit == 'days':
                self.calculated_stopping_tm = datetime.datetime.fromtimestamp(
                    self.started_tm.timestamp() + duration * 24 * 3600)

        if user:
            self.started_by_user = user

        # self.publish_or_hold_publications_on_plan_start()
        return self

    def stop(self, user=None):
        self.stopped_tm = datetime.datetime.utcnow()
        if user:
            self.stopped_by_user = user

        return self

    def publish_or_hold_publications_on_plan_start(self):

        utils.db.execute_function("membership_hold_unhold_publications('%s')" % (self.member_company_portal_id,))

        # from ..models.materials import Publication
        # count = self.member_company_portal.get_publication_count()
        # changes = {vis: {'holded': 0, 'unholded': 0, 'remain_holded': 0} for vis in Publication.VISIBILITIES}
        #
        # for vis in Publication.VISIBILITIES:
        #     count_vis = count['by_visibility_status'][vis]
        #     limit = getattr(self, 'publication_count_' + vis.lower())
        #     if count_vis['PUBLISHED'] > limit > 0:
        #         changes[vis]['holded'] = count_vis['PUBLISHED'] - limit
        #         g.db.query(Publication).filter(Publication.status == Publication.STATUSES['PUBLISHED']). \
        #             limit(changes[vis]['holded']).update({'status': Publication.STATUSES['HOLDED']})
        #     elif limit <= 0 or (count_vis['PUBLISHED'] < limit and count_vis['HOLDED'] > 0):
        #         changes[vis]['unholded'] = count_vis['HOLDED'] if limit <= 0 else min(count_vis['HOLDED'],
        #                                                                               limit - count_vis['PUBLISHED'])
        #         changes[vis]['remain_holded'] = count_vis['HOLDED'] - changes[vis]['unholded']
        #         g.db.query(Publication).filter(Publication.status == Publication.STATUSES['HOLDED']). \
        #             limit(changes[vis]['unholded']).update({'status': Publication.STATUSES['PUBLISHED']})
        #     else:
        #         changes[vis]['remain_holded'] = count_vis['HOLDED']
        #
        # self.member_company_portal.notify_company_about_holded_or_published_publication(changes)

        return self


def stop(self, user=None):
    self.stopped_tm = datetime.datetime.utcnow()
    if user:
        self.stopped_by_user = user


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

    status = Column(TABLE_TYPES['status'], default='APPLICANT', nullable=False)

    portal = relationship(Portal)

    company = relationship('Company')

    requested_membership_plan_issued_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan_issued.id'),
                                                 nullable=True)
    requested_membership_plan_issued = relationship('MembershipPlanIssued',
                                                    cascade="all, merge",
                                                    single_parent=True,
                                                    foreign_keys=[requested_membership_plan_issued_id])

    request_membership_plan_issued_immediately = Column(TABLE_TYPES['boolean'], nullable=False, default=False)

    current_membership_plan_issued_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan_issued.id'),
                                               nullable=True)

    current_membership_plan_issued = relationship('MembershipPlanIssued',
                                                  # backref='current_for_member_company_portal',
                                                  foreign_keys=[current_membership_plan_issued_id])

    STATUSES = {'APPLICANT': 'APPLICANT', 'REJECTED': 'REJECTED', 'ACTIVE': 'ACTIVE',
                'SUSPENDED': 'SUSPENDED', 'FROZEN': 'FROZEN', 'DELETED': 'DELETED'}

    def get_client_side_dict(self, fields='id,status,rights,portal_id,company_id,tags', more_fields=None):
        return self.to_dict(fields, more_fields)

    def portal_memberee_grid_row(self):
        from ..models.rights import MembershipRights
        return utils.dict_merge(self.get_client_side_dict(
            fields='id,status,portal.own_company,portal,rights,tags,current_membership_plan_issued,'
                   'requested_membership_plan_issued,request_membership_plan_issued_immediately'),
            {'publications': self.get_publication_count()},
            {'actions': MembershipRights(company=self.company_id, member_company=self).actions()})

    def company_member_grid_row(self):
        from ..models.rights import MembersRights
        return utils.dict_merge({'membership': self.get_client_side_dict(
            more_fields='company,current_membership_plan_issued,requested_membership_plan_issued,portal.company_owner_id')
        },
            {'publications': self.get_publication_count()},
            {'actions': MembersRights(company=self.portal.company_owner_id, member_company=self).actions()},
            {'id': self.id})

    def get_client_side_dict_for_plan(self):
        ret = {
            'membership': self.get_client_side_dict(
                fields='id,current_membership_plan_issued,requested_membership_plan_issued,'
                       'requested_membership_plan_issued.requested_by_user,'
                       'request_membership_plan_issued_immediately,'
                       'company.name,company.logo.url,portal.name, portal.logo.url, portal.default_membership_plan_id'),
            'select': {
                'plans': utils.get_client_side_list(self.portal.plans_active),
                'publications': self.get_publication_count()
            },
            'selected_by_user_plan_id': True if self.requested_membership_plan_issued else False
        }
        if int(float(ret['membership']['current_membership_plan_issued']['duration'].split(' ')[0])) < 0:
            ret['membership']['request_membership_plan_issued_immediately'] = True
        return ret

    def seo_dict(self):
        return {
            'title': self.company.name,
            'keywords': ','.join(t.text for t in self.tags),
            'description': self.company.short_description if self.company.short_description else self.company.about,
            'image_url': self.company.logo['url'] if self.company.logo['selected_by_user'][
                                                         'type'] == 'provenance' else None
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

            'division_id': PRElasticField(analyzed=False,
                                          setter=lambda: utils.db.query_filter(PortalDivision, portal_id=self.portal.id,
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

    @staticmethod
    def apply_company_to_portal(company_id, portal_id):
        from ..models.company import Company

        """Add company to MemberCompanyPortal table. Company will be partner of this portal"""
        membership = utils.db.query_filter(MemberCompanyPortal).filter_by(portal_id=portal_id,
                                                                          company_id=company_id).first()
        if membership:
            membership.set_client_side_dict(MemberCompanyPortal.STATUSES['APPLICANT'])
        else:
            membership = MemberCompanyPortal(id=utils.db.create_uuid(),
                                             company=Company.get(company_id),
                                             portal=utils.db.query_filter(Portal, id=portal_id).one())

        membership.current_membership_plan_issued = membership.create_issued_plan()
        membership.save().notify_portal_about_company_member("Company %s %s of membership at portal %s//##"
                                                             "this message is sent when company want to join to portal" % (
                                                                 utils.jinja.link_company_profile(),
                                                                 utils.jinja.link('url_portal_companies_members',
                                                                                  'aspire',
                                                                                  True),
                                                                 utils.jinja.link_external()))
        return membership

    def set_memberee_status(self, status):
        self.set_client_side_dict(status=status)
        self.save().notify_portal_about_company_member("Company %s changed status of membership to %s at portal %s" %
                                                       (utils.jinja.link_company_profile(),
                                                        utils.jinja.link('url_portal_companies_members', self.status,
                                                                         True),
                                                        utils.jinja.link_external()))
        return self

    def create_issued_plan(self, membership_plan: MembershipPlan = None, user=None):
        from ..constants.RECORD_IDS import SYSTEM_USERS
        plan = membership_plan if membership_plan else self.portal.default_membership_plan
        plan_is_default = self.portal.default_membership_plan_id == plan.id
        ret = MembershipPlanIssued(
            requested_by_user_id=user.id if user else SYSTEM_USERS.profireader(),
            portal_id=self.portal.id,
            auto_apply=plan.auto_apply or plan_is_default,
            confirmed=plan.auto_apply or plan_is_default,
            company_id=self.company.id,
            name=plan.name,
            price=-1 if plan_is_default else plan.price,
            currency_id=plan.currency_id,
            duration='-1 years' if plan_is_default else plan.duration,
            publication_count_open=plan.publication_count_open,
            publication_count_registered=plan.publication_count_registered,
            publication_count_payed=plan.publication_count_payed)

        ret.membership_plan = plan
        ret.member_company_portal_id = self.id

        return ret

    def requested_new_plan_issued(self, requested_plan_id, immediately):
        to_delete = None
        what_is_done = None
        if requested_plan_id is False:
            # user don't want any new plan
            self.requested_membership_plan_issued = None
            self.request_membership_plan_issued_immediately = False
        elif requested_plan_id is True:
            if self.requested_membership_plan_issued.auto_apply and immediately:
                self.current_membership_plan_issued.stop()
                self.current_membership_plan_issued = self.requested_membership_plan_issued
                self.current_membership_plan_issued.start()
                self.requested_membership_plan_issued = None
                self.request_membership_plan_issued_immediately = False
                what_is_done = 'started'
            else:
                self.request_membership_plan_issued_immediately = immediately
                what_is_done = 'planed' if self.requested_membership_plan_issued.auto_apply else 'requested'
        else:
            membership_plan = MembershipPlan.get(requested_plan_id)
            issued_plan = self.create_issued_plan(membership_plan, user=g.user)
            to_delete = self.requested_membership_plan_issued
            if immediately and \
                    (self.portal.default_membership_plan_id == requested_plan_id or membership_plan.auto_apply):
                self.current_membership_plan_issued.stop()
                self.current_membership_plan_issued = issued_plan
                self.current_membership_plan_issued.start()
                self.requested_membership_plan_issued = None
                self.request_membership_plan_issued_immediately = False
                what_is_done = 'started'
            else:
                self.requested_membership_plan_issued = issued_plan
                self.request_membership_plan_issued_immediately = immediately
                what_is_done = 'planed' if self.requested_membership_plan_issued.auto_apply else 'requested'
        self.save()
        if to_delete:
            to_delete.delete()
        if what_is_done:
            self.notify_portal_about_company_member(
                "Company %s just %s plan %s of membership at portal %s" %
                (utils.jinja.link_company_profile(),
                 utils.jinja.link('url_portal_companies_members', what_is_done, True),
                 self.requested_membership_plan_issued.name if
                 self.requested_membership_plan_issued else self.current_membership_plan_issued.name,
                 utils.jinja.link_external(),
                 ))
        return self

    def set_new_plan_issued(self, requested_plan_id, immediately):
        to_delete = None
        if requested_plan_id is True:
            if immediately:
                self.current_membership_plan_issued.stop()
                self.current_membership_plan_issued = self.requested_membership_plan_issued
                self.current_membership_plan_issued.start()
                self.requested_membership_plan_issued = None
                self.request_membership_plan_issued_immediately = False
            else:
                self.requested_membership_plan_issued.confirmed = True
        else:
            issued_plan = self.create_issued_plan(MembershipPlan.get(requested_plan_id), user=g.user)
            to_delete = self.requested_membership_plan_issued
            if immediately:
                self.current_membership_plan_issued.stop()
                self.current_membership_plan_issued = issued_plan
                self.current_membership_plan_issued.start()
                self.requested_membership_plan_issued = None
                self.request_membership_plan_issued_immediately = False
            else:
                self.requested_membership_plan_issued = issued_plan
                self.requested_membership_plan_issued.confirmed = True

        self.save()
        if to_delete:
            to_delete.delete()
        return self

    @staticmethod
    def get_by_portal_id_company_id(portal_id=None, company_id=None):
        return utils.db.query_filter(MemberCompanyPortal).filter_by(portal_id=portal_id, company_id=company_id).first()

    @staticmethod
    def get_members(company_id, *args):
        subquery = utils.db.query_filter(MemberCompanyPortal).filter(
            MemberCompanyPortal.portal_id == utils.db.query_filter(Portal,
                                                                   company_owner_id=company_id).subquery().c.id).filter(
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
            tag_pub = utils.db.query_filter(TagMembership).filter(and_(TagMembership.tag_id == tag.id,
                                                                       TagMembership.member_company_portal_id == self.id)).one()
            tag_pub.position = tag_position
            tag_pub.save()
        return self

    def get_publication_count(self):
        from ..models.materials import Publication, Material
        from sqlalchemy.sql import functions
        ret = {'by_status_visibility': {s: {v: 0 for v in Publication.VISIBILITIES} for s in Publication.STATUSES},
               'by_visibility_status': {v: {s: 0 for s in Publication.STATUSES} for v in Publication.VISIBILITIES},
               'by_status': {s: 0 for s in Publication.STATUSES},
               'by_visibility': {s: 0 for s in Publication.VISIBILITIES},
               'all': 0,
               }

        cnt = g.db.query(Publication.status, Publication.visibility, functions.count(Publication.id).label('cnt')). \
            join(Material, Publication.material_id == Material.id). \
            join(PortalDivision, Publication.portal_division_id == PortalDivision.id).filter(and_(
            Material.company_id == self.company_id,
            PortalDivision.portal_id == self.portal_id)).group_by(Publication.status, Publication.visibility).all()

        for c in cnt:
            ret['by_status_visibility'][c.status][c.visibility] = c.cnt
            ret['by_status'][c.status] += c.cnt
            ret['by_visibility_status'][c.visibility][c.status] = c.cnt
            ret['by_visibility'][c.visibility] += c.cnt
            ret['all'] += c.cnt

        return ret

    def notify_portal_about_company_member(self, phrase, rights=None):
        from ..models.messenger import Notification, Socket
        from ..models.rights import BaseRightsEmployeeInCompany
        from ..models.company import UserCompany

        rights = rights or UserCompany.RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES

        Socket.prepare_notifications(
            BaseRightsEmployeeInCompany(self.portal.own_company).get_user_with_rights(rights),
            Notification.NOTIFICATION_TYPES['PORTAL_COMPANIES_MEMBERS_ACTIVITY'],
            phrase,
            {
                'portal': self.portal,
                'company': self.company,
                'url_company_profile': url_for('company.profile', company_id=self.company.id),
                'url_portal_companies_members': utils.jinja.grid_url(self.id, 'portal.companies_members',
                                                                     portal_id=self.portal.id)
            },
            except_to_user=[g.user])()

    def notify_company_about_portal_memberee(self, phrase, rights=None):
        from ..models.messenger import Notification, Socket
        from ..models.rights import BaseRightsEmployeeInCompany
        from ..models.company import UserCompany

        rights = rights or UserCompany.RIGHT_AT_COMPANY.COMPANY_MANAGE_PARTICIPATION

        Socket.prepare_notifications(
            BaseRightsEmployeeInCompany(self.company).get_user_with_rights(rights),
            Notification.NOTIFICATION_TYPES['COMPANY_PORTAL_MEMBEREE_ACTIVITY'], phrase,
            {
                'portal': self.portal,
                'company': self.company,
                'url_company_profile': url_for('company.profile', company_id=self.company.id),
                'url_company_portal_memberees': utils.jinja.grid_url(self.id, 'company.portal_memberees',
                                                                     company_id=self.company.id)
            },
            except_to_user=[g.user])()

    def notify_company_about_holded_or_published_publication(self, changes):
        from ..models.materials import Publication
        from ..models.messenger import Socket, Notification
        from ..models.rights import PublishUnpublishInPortal

        d = None
        phrases = []
        dictionaries = []

        for vis in Publication.VISIBILITIES:
            phrase = None
            if changes[vis]['holded']:
                phrase = "%s was holded"
                d = {'cnt': changes[vis]['holded']}
            elif changes[vis]['unholded']:
                phrase = "%s was unholded"
                d = {'cnt': changes[vis]['unholded']}
            elif changes[vis]['remain_holded']:
                phrase = "%s still remain holded"
                d = {'cnt': changes[vis]['remain_holded']}
            if phrase:
                phrase = phrase % (vis,)
                if not len(phrases):
                    phrases.append(
                        "Due to new plan was applied for company %s at portal %s some changes with your publication was made" %
                        (utils.jinja.link_company_profile(), utils.jinja.link_external()))
                    dictionaries.append({
                        'portal': self.portal,
                        'company': self.company,
                        'url_company_profile': url_for('company.profile', company_id=self.company.id)
                    })

                phrases.append("%(count)s" + phrase)
                dictionaries.append(d)

        if len(phrases):
            to_users = PublishUnpublishInPortal(None, None, self.portal.own_company, self.portal).get_user_with_rights(
                PublishUnpublishInPortal.publish_rights)
            Socket.prepare_notifications(to_users, Notification.NOTIFICATION_TYPES['PUBLICATION_ACTIVITY'], phrases,
                                         dictionaries)()

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

    def notify_company_about_deleted_publications(self, because_of):
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
            phrase = "Because of %s user %s just complitelly deleted a material named `%%(material.title)s` from portal %s" % \
                     (because_of, utils.jinja.link_user_profile(), utils.jinja.link_external())

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
        return utils.db.query_filter(PortalDivisionType).all()


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
                           for division in utils.db.query_filter(PortalDivision.id, PortalDivision.name,
                                                                 portal_id=self.portal_id).all()},
                          ensure_ascii=False)

    @staticmethod
    def get_portals_for_user():
        portals = utils.db.query_filter(Portal).filter(
            ~(Portal.id.in_(utils.db.query_filter(UserPortalReader.portal_id, user_id=g.user.id)))).all()
        for portal in portals:
            yield (portal.id, portal.name,)

    @staticmethod
    def get(user_id=None, portal_id=None):
        return utils.db.query_filter(UserPortalReader).filter_by(user_id=user_id, portal_id=portal_id).first()

    @staticmethod
    def get_portals_and_plan_info_for_user(user_id, page, items_per_page, filter_params):
        from ..controllers.pagination import pagination
        query, pages, page, count = pagination(
            utils.db.query_filter(UserPortalReader, user_id=user_id).filter(filter_params),
            page=int(page), items_per_page=int(items_per_page))

        for upr in query:
            yield dict(id=upr.id, portal_id=upr.portal_id, status=upr.status, start_tm=upr.start_tm,
                       portal_logo=upr.portal.logo['url'],
                       end_tm=upr.end_tm if upr.end_tm > datetime.datetime.utcnow() else 'Expired at ' + upr.end_tm,
                       plan_id=upr.portal_plan_id,
                       plan_name=utils.db.query_filter(ReaderUserPortalPlan.name, id=upr.portal_plan_id).one()[0],
                       portal_name=upr.portal.name, portal_host=upr.portal.host, amount=upr.amount,
                       portal_divisions=[{division.name: division.id}
                                         for division in upr.portal.divisions])

    @staticmethod
    def get_filter_for_portals_and_plans(portal_name=None, start_end_tm=None, package_name=None):
        filter_params = []
        if portal_name:
            filter_params.append(UserPortalReader.portal_id.in_(utils.db.query_filter(Portal.id).filter(
                Portal.name.ilike('%' + portal_name + '%'))))
        if start_end_tm:
            from_tm = datetime.datetime.utcfromtimestamp(int(start_end_tm['from'] + 1) / 1000)
            to_tm = datetime.datetime.utcfromtimestamp(int(start_end_tm['to'] + 86399999) / 1000)
            filter_params.extend([UserPortalReader.start_tm >= from_tm,
                                  UserPortalReader.start_tm <= to_tm])
        if package_name:
            filter_params.append(
                UserPortalReader.portal_plan_id == utils.db.query_filter(ReaderUserPortalPlan.id).filter(
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
