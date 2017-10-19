import datetime
import json
import re
from functools import reduce

import simplejson
from flask import g, url_for, current_app
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_, or_, expression

from config import Config
from .elastic import PRElasticField, PRElasticDocument
from .files import FileImageCrop, FileImgDescriptor
from .pr_base import PRBase, Base
from .. import utils
from ..constants.RECORD_IDS import FOLDER_AND_FILE
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..models.tag import Tag, TagMembership
import calendar
from profapp.constants.NOTIFICATIONS import NOTIFICATION_TYPES


class Portal(Base, PRBase):
    __tablename__ = 'portal'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['name'])
    host = Column(TABLE_TYPES['short_name'], default='')
    lang = Column(TABLE_TYPES['short_name'])

    STATUSES = {'PORTAL_ACTIVE': 'PORTAL_ACTIVE'}

    status = Column(TABLE_TYPES['status'], default='PORTAL_ACTIVE')

    aliases = Column(TABLE_TYPES['text'], default='')

    url_facebook = Column(TABLE_TYPES['url'])
    url_google = Column(TABLE_TYPES['url'])
    url_twitter = Column(TABLE_TYPES['url'])
    url_linkedin = Column(TABLE_TYPES['url'])
    # url_vkontakte = Column(TABLE_TYPES['url'])

    google_analytics_account_id = Column(TABLE_TYPES['string_100'])
    google_analytics_web_property_id = Column(TABLE_TYPES['string_100'])
    google_analytics_view_id = Column(TABLE_TYPES['string_100'])
    google_analytics_dimensions = Column(TABLE_TYPES['json'])
    google_analytics_metrics = Column(TABLE_TYPES['json'])

    company_owner_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), unique=True)
    portal_layout_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_layout.id'))

    logo_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImageCrop.id), nullable=True)
    logo_file_img = relationship(FileImageCrop, uselist=False, foreign_keys=[logo_file_img_id])
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

    favicon_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImageCrop.id), nullable=True)
    favicon_file_img = relationship(FileImageCrop, uselist=False, foreign_keys=[favicon_file_img_id])
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
                         primaryjoin='and_(Portal.id == MembershipPlan.portal_id, MembershipPlan.status != \'MEMBERSHIP_PLAN_DELETED\')')

    plans_active = relationship('MembershipPlan',
                                cascade="all, merge, delete-orphan",
                                order_by='asc(MembershipPlan.position)',
                                primaryjoin='and_(Portal.id==MembershipPlan.portal_id, MembershipPlan.status == \'MEMBERSHIP_PLAN_ACTIVE\')')

    divisions = relationship('PortalDivision',
                             # backref='portal',
                             cascade="all, merge, delete-orphan",
                             order_by='asc(PortalDivision.position)',
                             primaryjoin='Portal.id==PortalDivision.portal_id')

    divisions_publicable = relationship('PortalDivision',
                                        viewonly=True,
                                        order_by='asc(PortalDivision.position)',
                                        primaryjoin="and_(Portal.id==PortalDivision.portal_id, PortalDivision.portal_division_type_id.in_(['events', 'news']))")

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


    def __init__(self, **kwargs):
        super(Portal, self).__init__(**kwargs)
        if not self.portal_layout_id:
            self.portal_layout_id = utils.db.query_filter(PortalLayout).first().id

    def is_active(self):
        return True

    def setup_ssl(self):
        bashCommand = "ssh -i ./scrt/id_rsa_haproxy root@haproxy.profi /bin/bash /usr/local/bin/certbot_front.sh {}".format(
            self.host)
        import subprocess
        process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
        output, error = process.communicate()
        # print(bashCommand, output, error)
        # current_app.log.notice("running bash command for ssl: {}, output={}, error={}".format(bashCommand, output, error)) 
        return True

    def update_google_analytics_host(self, ga_man):
        ga_man.update_host_for_property(
            self.google_analytics_account_id, self.google_analytics_web_property_id, new_host=self.host)
        ga_man.update_host_for_view(
            self.google_analytics_account_id, self.google_analytics_web_property_id, self.google_analytics_view_id,
            new_host=self.host)

    def setup_google_analytics(self, ga_man, force_recreate=False):
        if force_recreate or not self.google_analytics_account_id:
            self.google_analytics_account_id, self.google_analytics_web_property_id, self.google_analytics_view_id = \
                ga_man.create_web_property_and_view(self.host)
            self.google_analytics_dimensions, self.google_analytics_metrics = \
                ga_man.create_custom_dimensions_and_metrics(
                    self.google_analytics_account_id, self.google_analytics_web_property_id)

    @staticmethod
    def launch_new_portal(company):
        from ..models.permissions import RIGHT_AT_PORTAL
        # This all ids (by db_utils.create_uuid()) we need because we have mutual foreign keys in database and
        # NOT NULL constrain (and not null constrain don't support deferrable property')

        ret = Portal(host='', lang=g.user.lang,
                     id=utils.db.create_uuid(),
                     own_company=company,
                     company_owner_id=company.id,
                     default_membership_plan_id=utils.db.create_uuid(),
                     company_memberships=[
                         MemberCompanyPortal(
                             id=utils.db.create_uuid(),
                             company=company,
                             rights={RIGHT_AT_PORTAL._OWNER: True},
                             status=MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE'])])

        ret.default_membership_plan = MembershipPlan(name='default', position=0,
                                                     portal_id=ret.id,
                                                     status=MembershipPlan.STATUSES['MEMBERSHIP_PLAN_ACTIVE'],
                                                     duration='1 years',
                                                     publication_count_open=-1,
                                                     publication_count_registered=10,
                                                     publication_count_payed=0,
                                                     price=1, currency_id='UAH')

        ret.company_memberships[0].portal = ret

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

        self.host = self.host.lower()

        if any([re.match('^' + h + ('.' + Config.MAIN_DOMAIN).replace('.', '\.') + '$', self.host) for h in
                ['file[0-9]+', 'ads', 'elk', 'mail', 'socket', 'static', 'ns[0-9]', 'www']]):
            errors['host'] = 'this hostname is registered'

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
            if len([x for x in self.divisions if x.name == div.name]) > 1:
                utils.dict_deep_replace('pls use unique names for divisions', warnings, 'divisions', div.id, 'name')

            if len([x for x in self.divisions if x.get_url() == div.get_url()]) > 1:
                utils.dict_deep_replace('pls use unique urls', errors, 'divisions', div.id, 'url')

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
                from ..models.materials import Publication
                from sqlalchemy.sql import functions

                if d.portal_division_type.id in [PortalDivision.TYPES['events'], PortalDivision.TYPES['news']]:
                    cnt = g.db.query(Publication.status, Publication.visibility,
                                     functions.count(Publication.id).label('cnt')). \
                        filter(and_(Publication.portal_division_id == d.id)). \
                        group_by(Publication.status, Publication.visibility).all()
                    utils.find_by_id(ret['divisions'], d.id)[
                        'publication_count'] = Publication.group_by_status_and_visibility(cnt)

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

    def get_analytics(self, page_type, company_id='__NA__',
                      publication_visibility='__NA__', publication_reached='__NA__'):
        from profapp.models.third.google_analytics_management import PortalAnalytics
        from profapp.models.portal import UserPortalReader
        user_portal_reader = UserPortalReader.get_by_portal_id_user_id(self.id)

        return PortalAnalytics(
            page_type=page_type, company_id=company_id,
            income=len([a for a in self.advs if re.match(r'.*data-revive-id.*', str(a.html), re.DOTALL)]),
            publication_visibility=publication_visibility, publication_reached=publication_reached,
            reader_plan=user_portal_reader.portal_plan_id if user_portal_reader else '__NA__')

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


class PortalLayout(Base, PRBase):
    __tablename__ = 'portal_layout'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
    name = Column(TABLE_TYPES['name'], nullable=False)
    path = Column(TABLE_TYPES['name'], nullable=False)
    hidden = Column(TABLE_TYPES['boolean'], nullable=False, default=False)

    def get_client_side_dict(self, fields='id|name', more_fields=None):
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
        for r in ret:
            r['actions'] = [{'enabled': enabled, 'name': name, 'message': ''} for name, enabled in r['actions'].items()]
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

    STATUSES = {'MEMBERSHIP_PLAN_ACTIVE': 'MEMBERSHIP_PLAN_ACTIVE',
                'MEMBERSHIP_PLAN_DELETED': 'MEMBERSHIP_PLAN_DELETED'}

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

    def start(self):

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

                _, monthdays = calendar.monthrange(self.started_tm.year + add_year, new_month)
                self.calculated_stopping_tm = self.started_tm.replace(year=self.started_tm.year + add_year,
                                                                      month=new_month,
                                                                      day=min(self.started_tm.day, monthdays))


            elif duration_unit == 'weeks':
                self.calculated_stopping_tm = datetime.datetime.fromtimestamp(
                    self.started_tm.timestamp() + duration * 7 * 24 * 3600)
            elif duration_unit == 'days':
                self.calculated_stopping_tm = datetime.datetime.fromtimestamp(
                    self.started_tm.timestamp() + duration * 24 * 3600)

        if getattr(g, 'user', None):
            self.started_by_user = g.user

        return self.save().publish_or_hold_publications_on_plan_start()

    def publish_or_hold_publications_on_plan_start(self):

        from ..models.materials import Publication
        from ..models.translate import TranslateTemplate, Phrase

        old_count = self.member_company_portal.get_publication_count()
        for vis in Publication.VISIBILITIES:
            for p_id in utils.db.execute_function("membership_hold_unhold_publications('%s', '%s')" %
                                                          (self.member_company_portal_id, vis)):
                p = Publication.get(p_id)
                p.md_tm = None
                p.save()

        new_count = self.member_company_portal.get_publication_count()

        phrases_changes = []
        phrases_remain = []

        visibility_translation = {vis: TranslateTemplate.translate_and_substitute(
            '', '__PUBLICATION_VISIBILITY_' + vis, phrase_default=vis) for vis in Publication.VISIBILITIES}

        for vis in Publication.VISIBILITIES:

            changes = new_count['by_visibility_status'][vis]['PUBLISHED'] - \
                      old_count['by_visibility_status'][vis]['PUBLISHED']

            if changes > 0:
                phrases_changes.append(Phrase(
                    '%(count)s publications of visibility %(visibility)s was unholded',
                    dict={'count': changes, 'visibility': visibility_translation[vis]}))
            elif changes < 0:
                phrases_changes.append(Phrase(
                    "%(count)s publications of visibility %(visibility)s was holded",
                    dict={'count': -changes, 'visibility': visibility_translation[vis]}))
            if new_count['by_visibility_status'][vis]['HOLDED'] > 0 and changes > 0:
                phrases_remain.append(Phrase(
                    "%(count)s publications of visibility %(visibility)s remain holded",
                    dict={'count': new_count['by_visibility_status'][vis]['HOLDED'],
                          'visibility': visibility_translation[vis]}))

        if phrases_changes or phrases_remain:
            if phrases_changes:
                self.member_company_portal.NOTIFY_ARTICLE_VISIBILITY_CHANGED_BY_PLAN_MEMBERSHIP_CHANGE(
                    more_phrases_to_portal=phrases_changes + phrases_remain,
                    more_phrases_to_company=phrases_changes + phrases_remain)
            else:
                self.member_company_portal.NOTIFY_ARTICLE_STILL_HOLDED_DESPITE_BY_PLAN_MEMBERSHIP_CHANGE(
                    more_phrases_to_portal=phrases_changes + phrases_remain,
                    more_phrases_to_company=phrases_changes + phrases_remain)

    def stop(self, user=None):
        self.stopped_tm = datetime.datetime.utcnow()
        if user:
            self.stopped_by_user = user

        return self


from profapp.constants.NOTIFICATIONS import NotifyMembershipChange


class MemberCompanyPortal(Base, PRBase, PRElasticDocument, NotifyMembershipChange):
    from ..models.permissions import RIGHT_AT_COMPANY, RIGHT_AT_PORTAL
    __tablename__ = 'member_company_portal'

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

    status = Column(TABLE_TYPES['status'], nullable=False)

    portal = relationship(Portal)

    company = relationship('Company')

    requested_membership_plan_issued_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan_issued.id'),
                                                 nullable=True)
    requested_membership_plan_issued = relationship('MembershipPlanIssued',
                                                    cascade="all",
                                                    single_parent=True,
                                                    foreign_keys=[requested_membership_plan_issued_id])

    request_membership_plan_issued_immediately = Column(TABLE_TYPES['boolean'], nullable=False, default=False)

    current_membership_plan_issued_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('membership_plan_issued.id'),
                                               nullable=True)

    current_membership_plan_issued = relationship('MembershipPlanIssued',
                                                  foreign_keys=[current_membership_plan_issued_id])

    STATUSES = {'MEMBERSHIP_REQUESTED_BY_COMPANY': 'MEMBERSHIP_REQUESTED_BY_COMPANY',
                'MEMBERSHIP_REQUESTED_BY_PORTAL': 'MEMBERSHIP_REQUESTED_BY_PORTAL',
                'MEMBERSHIP_ACTIVE': 'MEMBERSHIP_ACTIVE',
                'MEMBERSHIP_SUSPENDED_BY_COMPANY': 'MEMBERSHIP_SUSPENDED_BY_COMPANY',
                'MEMBERSHIP_SUSPENDED_BY_PORTAL': 'MEMBERSHIP_SUSPENDED_BY_PORTAL',
                'MEMBERSHIP_CANCELED_BY_COMPANY': 'MEMBERSHIP_CANCELED_BY_COMPANY',
                'MEMBERSHIP_CANCELED_BY_PORTAL': 'MEMBERSHIP_CANCELED_BY_PORTAL'}

    DELETED_STATUSES = [STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY'], STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']]

    def status_changes_by_portal(self):
        from profapp.models.permissions import RIGHT_AT_COMPANY
        from ..models.company import UserCompany
        r = UserCompany.get_by_user_and_company_ids(company_id=self.portal.company_owner_id).rights[
            RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]

        if not r:
            return False

        changes = {s: {'status': s, 'enabled': r, 'message': ''} for s in MemberCompanyPortal.STATUSES}

        if self.company_id == self.portal.company_owner_id:
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_CANCELED_BY_PORTAL']]['message'] = 'You can`t cancel membership at portal of own company'
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_CANCELED_BY_PORTAL']]['enabled'] = False
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_SUSPENDED_BY_PORTAL']]['message'] = 'You can`t suspend membership at portal of own company'
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_SUSPENDED_BY_PORTAL']]['enabled'] = False

        if self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_PORTAL']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_REQUESTED_BY_PORTAL']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_REQUESTED_BY_COMPANY']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_PORTAL']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_COMPANY']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']]
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']:
            return []
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']:
            return []

    def status_changes_by_company(self):
        from ..models.company import UserCompany
        from ..models.permissions import RIGHT_AT_COMPANY

        r = UserCompany.get_by_user_and_company_ids(company_id=self.company_id).rights[
            RIGHT_AT_COMPANY.COMPANY_REQUIRE_MEMBEREE_AT_PORTALS]

        if not r:
            return False

        changes = {s: {'status': s, 'enabled': r, 'message': ''} for s in MemberCompanyPortal.STATUSES}

        if self.company_id == self.portal.company_owner_id:
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_CANCELED_BY_COMPANY']]['message'] = 'You can`t cancel membership at portal of own company'
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_CANCELED_BY_COMPANY']]['enabled'] = False
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_SUSPENDED_BY_COMPANY']]['message'] = 'You can`t suspend membership at portal of own company'
            changes[MemberCompanyPortal.STATUSES[
                'MEMBERSHIP_SUSPENDED_BY_COMPANY']]['enabled'] = False

        if self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_COMPANY']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_REQUESTED_BY_COMPANY']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_REQUESTED_BY_PORTAL']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_COMPANY']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']],
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']],
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_SUSPENDED_BY_PORTAL']:
            return [
                changes[MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']]
            ]
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_COMPANY']:
            return []
        elif self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_CANCELED_BY_PORTAL']:
            return []

    def get_client_side_dict(self, fields='id,status,rights,portal_id,company_id,tags', more_fields=None):
        return self.to_dict(fields, more_fields)

    def portal_memberee_grid_row(self):
        return {
            'id': self.id,
            'membership': self.get_client_side_dict(
                fields='id,status,portal.own_company,portal,rights,tags,current_membership_plan_issued,'
                       'requested_membership_plan_issued,request_membership_plan_issued_immediately,company.id|name'),
            'publications': self.get_publication_count(),
            'status_changes': self.status_changes_by_company(),
        }

    def company_member_grid_row(self):
        return {
            'id': self.id,
            'membership': self.get_client_side_dict(
                more_fields='portal.name|host|id,company,current_membership_plan_issued,requested_membership_plan_issued,portal.company_owner_id'),
            'publications': self.get_publication_count(),
            'status_changes': self.status_changes_by_portal(),
        }

    def material_or_publication_grid_row(self, material):
        from profapp.models.materials import Publication
        from profapp.models.permissions import ActionsForMaterialAtMembership, ActionsForPublicationAtMembership
        ret = self.get_client_side_dict(fields='id, portal.id|name|host, portal.logo.url, portal.own_company.name|id, '
                                               'portal.own_company.logo.url')

        publication = g.db.query(Publication).filter(and_(
            Publication.material_id == material.id,
            Publication.portal_division_id.in_([div.id for div in self.portal.divisions]))).first()
        if publication:
            ret['publication'] = publication.get_client_side_dict(
                'id,status,visibility,publishing_tm,tags,portal_division.id|name,portal_division.portal.id|name|host')
            ret['actions'] = ActionsForPublicationAtMembership.actions(self, publication=publication)
        else:
            ret['publication'] = None
            # we remove this action because we have button in $publish dialog
            ret['actions'] = [a for a in ActionsForMaterialAtMembership.actions(self, material)]

        return ret

    # def get_publication_dict(publication):
    #     return {
    #         'publication': publication.get_client_side_dict(),
    #         'id': publication.id,
    #         'actions': permissions.ActionsForPublicationAtMembership.actions()
    #     }

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
        if self.status != MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE']:
            return False
        return True

    @staticmethod
    def apply_company_to_portal(company_id, portal_id):
        from ..models.company import Company

        membership = \
            MemberCompanyPortal.get_by_portal_id_company_id(portal_id=portal_id, company_id=company_id) or \
            MemberCompanyPortal(id=utils.db.create_uuid(),
                                company=Company.get(company_id),
                                portal=utils.db.query_filter(Portal, id=portal_id).one())

        if not membership.status or membership.status in MemberCompanyPortal.DELETED_STATUSES:
            membership.status = MemberCompanyPortal.STATUSES['MEMBERSHIP_REQUESTED_BY_COMPANY']
            membership.NOTIFY_MEMBERSHIP_REQUESTED_BY_COMPANY()
            membership.current_membership_plan_issued = membership.create_issued_plan()
            membership.save()

        return membership

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

        # requested_plan_id == False/True/id =Do nothing/use already issued plan/reissue plan by id

        to_delete = None
        if requested_plan_id is False:
            # user don't want any new plan
            self.requested_membership_plan_issued = None
            self.request_membership_plan_issued_immediately = False

        else:
            issued_plan = self.requested_membership_plan_issued if requested_plan_id is True else self.create_issued_plan(
                MembershipPlan.get(requested_plan_id), user=g.user)

            plan_can_be_started_by_company = (issued_plan.auto_apply or
                                              self.portal.default_membership_plan_id == requested_plan_id)

            if immediately and plan_can_be_started_by_company:
                self.current_membership_plan_issued.stop()
                old_plan_name = self.current_membership_plan_issued.name
                self.current_membership_plan_issued = issued_plan
                self.current_membership_plan_issued.start()
                self.requested_membership_plan_issued = None
                self.request_membership_plan_issued_immediately = False
                self.NOTIFY_PLAN_STARTED_BY_COMPANY(new_plan_name=self.current_membership_plan_issued.name,
                                                    old_plan_name=old_plan_name)
            else:
                if requested_plan_id is not True:
                    to_delete = self.requested_membership_plan_issued
                    self.requested_membership_plan_issued = issued_plan
                self.request_membership_plan_issued_immediately = immediately

                if plan_can_be_started_by_company:
                    self.NOTIFY_PLAN_SCHEDULED_BY_COMPANY(
                        new_plan_name=self.requested_membership_plan_issued.name,
                        date_to_start=self.current_membership_plan_issued.calculated_stopping_tm)
                else:
                    self.NOTIFY_PLAN_REQUESTED_BY_COMPANY(
                        requested_plan_name=self.requested_membership_plan_issued.name)

        self.save()

        if to_delete:
            to_delete.delete()

        return self

    def set_new_plan_issued(self, requested_plan_id, immediately):
        to_delete = self.requested_membership_plan_issued if requested_plan_id is not True else None
        old_plan_name = self.current_membership_plan_issued.name

        if immediately:
            self.current_membership_plan_issued.stop()
            self.current_membership_plan_issued = self.requested_membership_plan_issued if requested_plan_id is True \
                else self.create_issued_plan(MembershipPlan.get(requested_plan_id), user=g.user)
            self.current_membership_plan_issued.start()
            self.requested_membership_plan_issued = None
            self.request_membership_plan_issued_immediately = False
            self.NOTIFY_PLAN_STARTED_BY_PORTAL(new_plan_name=self.current_membership_plan_issued.name,
                                               old_plan_name=old_plan_name)
        else:
            if requested_plan_id is True:
                if not self.requested_membership_plan_issued.confirmed:
                    self.NOTIFY_PLAN_CONFIRMED_BY_PORTAL(
                        new_plan_name=self.requested_membership_plan_issued.name,
                        old_plan_name=old_plan_name,
                        date_to_start=self.current_membership_plan_issued.calculated_stopping_tm)
            else:
                self.requested_membership_plan_issued = self.create_issued_plan(MembershipPlan.get(requested_plan_id),
                                                                                user=g.user)
                self.NOTIFY_PLAN_SCHEDULED_BY_PORTAL(
                    new_plan_name=self.requested_membership_plan_issued.name,
                    date_to_start=self.current_membership_plan_issued.calculated_stopping_tm)

            self.requested_membership_plan_issued.confirmed = True

        self.save()

        if to_delete:
            to_delete.delete()

        return self

    @staticmethod
    def get_by_portal_id_company_id(portal_id=None, company_id=None):
        return utils.db.query_filter(MemberCompanyPortal).filter_by(portal_id=portal_id, company_id=company_id).first()

    @staticmethod
    def search_for_portal_to_join(company_id, searchtext):
        return [p.get_client_side_dict() for p in
                g.db.query(Portal).outerjoin(MemberCompanyPortal, and_(MemberCompanyPortal.portal_id == Portal.id,
                                                                       MemberCompanyPortal.company_id == company_id)).
                    filter(Portal.name.ilike("%" + searchtext + "%")).
                    filter(or_(
                    MemberCompanyPortal.status.in_(MemberCompanyPortal.DELETED_STATUSES),
                    MemberCompanyPortal.status == None)).
                    filter(Portal.status.in_([Portal.STATUSES['PORTAL_ACTIVE']])).
                    all()]

    def has_rights(self, rightname):
        if self.portal.own_company.id == self.company_id:
            return True

        if rightname == '_OWNER':
            return False

        if rightname == '_ANY':
            return True if self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE'] else False
        return True if (
            self.status == MemberCompanyPortal.STATUSES['MEMBERSHIP_ACTIVE'] and self.rights[rightname]) else False

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
        from profapp.models.materials import Publication, Material
        from sqlalchemy.sql import functions

        cnt = g.db.query(Publication.status, Publication.visibility, functions.count(Publication.id).label('cnt')). \
            join(Material, Publication.material_id == Material.id). \
            join(PortalDivision, Publication.portal_division_id == PortalDivision.id).filter(and_(
            Material.company_id == self.company_id,
            PortalDivision.portal_id == self.portal_id)).group_by(Publication.status, Publication.visibility).all()

        return Publication.group_by_status_and_visibility(cnt)

    def _send_notification_about_membership_change(
            self, text, dictionary={}, comment='',
            rights_at_company=RIGHT_AT_COMPANY.COMPANY_MANAGE_PARTICIPATION,
            notification_type_to_company_employees=NOTIFICATION_TYPES['MEMBERSHIP_PORTAL_ACTIVITY'],
            rights_at_portal=RIGHT_AT_COMPANY.PORTAL_MANAGE_MEMBERS_COMPANIES,
            notification_type_to_portal_employees=NOTIFICATION_TYPES['MEMBERSHIP_COMPANY_ACTIVITY'],
            more_phrases_to_company=[], more_phrases_to_portal=[], except_to_user=None):

        from ..models.messenger import Socket
        from ..models.translate import Phrase

        phrase_comment = (' when ' + comment) if comment is None else ''

        more_phrases_to_company = more_phrases_to_company if isinstance(more_phrases_to_company, list) else \
            [more_phrases_to_company]
        more_phrases_to_portal = more_phrases_to_portal if isinstance(more_phrases_to_portal, list) else \
            [more_phrases_to_portal]

        grid_url = lambda endpoint, **kwargs: utils.jinja.grid_url(self.id, endpoint=endpoint, **kwargs)

        default_dict = {
            'company': self.company,
            'portal': self.portal,
            'url_company_profile': url_for('company.profile', company_id=self.company.id),
            'url_company_portal_memberees': grid_url('company.portal_memberees', company_id=self.company.id),
            'url_portal_companies_members': grid_url('portal.companies_members', portal_id=self.portal.id)
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
            user_who_made_changes_phrase + "%s of your company %s in portal %s just made following: " % \
            (utils.jinja.link('url_company_portal_memberees', 'membership', True),
             utils.jinja.link_company_profile(),
             utils.jinja.link_external()) + text, dict=all_dictionary_data,
            comment="to member company employees with rights %s%s" % (
                ','.join(rights_at_company), phrase_comment))

        phrase_to_employees_at_portal = Phrase(
            user_who_made_changes_phrase + "%s of company %s in your portal %s just made following: " % \
            (utils.jinja.link('url_portal_companies_members', 'membership', True),
             utils.jinja.link_company_profile(),
             utils.jinja.link_external()) +
            text, dict=all_dictionary_data,
            comment="to portal owner company employees with rights %s%s" % (
                ','.join(rights_at_portal), phrase_comment))

        users_at_company = self.company.get_user_with_rights(rights_at_company)
        users_at_portal = self.portal.own_company.get_user_with_rights(rights_at_portal)

        if self.company == self.portal.own_company:
            users_at_company = list(set(users_at_company) - set(users_at_portal))

        Socket.prepare_notifications(
            users_at_company,
            notification_type_to_company_employees,
            [phrase_to_employees_at_company] + more_phrases_to_company, except_to_user=except_to_user)

        Socket.prepare_notifications(
            users_at_portal,
            notification_type_to_portal_employees,
            [phrase_to_employees_at_portal] + more_phrases_to_portal, except_to_user=except_to_user)

        return lambda: utils.do_nothing()


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
        if instance.portal_division_type.id == PortalDivision.TYPES['custom_html']:
            return {
                'id': instance.portal_division_settings.id,
                'custom_html': instance.portal_division_settings.custom_html
            }
        elif instance.portal_division_type.id == PortalDivision.TYPES['company_subportal']:
            return {
                'id': instance.portal_division_settings.id,
                'company_id': instance.portal_division_settings.member_company_portal.company_id
            }
        else:
            return {}

    # def proxy_setter(self, file_image_crop: FileImageCrop, client_data):
    def __set__(self, instance, data):
        from .gallery import MaterialImageGallery
        if instance.portal_division_type.id == PortalDivision.TYPES['company_subportal']:
            membership = next(
                cm for cm in instance.portal.company_memberships if cm.company.id == data['company_id'])
            if not instance.portal_division_settings:
                instance.portal_division_settings = \
                    PortalDivisionSettings(portal_division=instance, member_company_portal=membership)
            instance.portal_division_settings.member_company_portal.company_id = membership.company.id
        elif instance.portal_division_type.id == PortalDivision.TYPES['custom_html']:
            if not instance.portal_division_settings:
                instance.portal_division_settings = \
                    PortalDivisionSettings(portal_division=instance, custom_html=data.get('custom_html', ''))

            # (instance.portal_division_settings.custom_html, instance.image_galleries) = \
            #     MaterialImageGallery.check_html(data.get('custom_html', ''), data.get('image_galleries', []),
            #                                     instance.image_galleries)

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
    url = Column(TABLE_TYPES['string_1000'], default='')

    position = Column(TABLE_TYPES['int'])

    portal = relationship(Portal, uselist=False)

    portal_division_type = relationship('PortalDivisionType', uselist=False)

    portal_division_settings = relationship('PortalDivisionSettings',
                                            uselist=False,
                                            cascade="all, merge, delete-orphan")

    settings = PortalDivisionSettingsDescriptor()

    tags = relationship(Tag, secondary='tag_portal_division', uselist=True)

    publications = relationship('Publication', cascade="all, delete-orphan")

    # image_galleries = relationship('MaterialImageGallery', cascade="all")

    TYPES = {'company_subportal': 'company_subportal', 'custom_html': 'custom_html', 'index': 'index', 'news': 'news',
             'events': 'events',
             'catalog': 'catalog'}

    def seo_dict(self):
        return {
            'title': self.html_title if self.html_title else self.name,
            'keywords': self.html_keywords if self.html_keywords else ','.join(t.text for t in self.tags),
            'description': self.html_description
        }

    def get_url(self):
        from profapp import TransliterationConverter
        if self.portal_division_type_id == 'index':
            return None
        return self.url if self.url else TransliterationConverter.transliterate(self.portal.lang, self.name)

    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id|portal_division_type_id|tags|settings|name|html_title|html_keywords|html_description',
                             more_fields=None):
        return self.to_dict(fields, more_fields)


class PortalDivisionSettings(Base, PRBase):
    __tablename__ = 'portal_division_settings'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    portal_division = relationship(PortalDivision, cascade="all, merge, delete")

    member_company_portal = relationship(MemberCompanyPortal)
    member_company_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('member_company_portal.id'))

    custom_html = Column(TABLE_TYPES['text'])


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
    def get_by_portal_id_user_id(portal_id, user_id=None):
        return utils.db.query_filter(UserPortalReader).filter_by(user_id=user_id if user_id else g.user_id,
                                                                 portal_id=portal_id).first()

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
