from datetime import datetime

import simplejson, re
from flask import g, session, url_for
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import and_, expression

from config import Config
from .elastic import PRElasticField, PRElasticDocument
from .files import FileImageCrop, FileImgDescriptor
from .pr_base import PRBase, Base, Grid
from .. import utils
from ..constants.RECORD_IDS import FOLDER_AND_FILE
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..models.company import Company, UserCompany
from ..models.portal import PortalDivision, Portal, MemberCompanyPortal
from ..models.tag import Tag, TagPublication
from ..models.users import User
from sqlalchemy.orm import validates


class Material(Base, PRBase, PRElasticDocument):
    __tablename__ = 'material'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    # portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))

    # TODO: OZ by OZ: remove me
    _del_image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=True)

    illustration_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImageCrop.id), nullable=True)
    illustration_file_img = relationship(FileImageCrop, uselist=False)

    illustration = FileImgDescriptor(relation_name='illustration_file_img',
                                     file_decorator=lambda m, r, f: f.attr(
                                         name='%s_for_material_illustration_%s' % (f.name, m.id),
                                         parent_id=m.company.system_folder_file_id,
                                         root_folder_id=m.company.system_folder_file_id),
                                     image_size=[600, 480],
                                     min_size=[600 / 8, 480 / 8],
                                     aspect_ratio=[600 / 480., 600 / 480.],
                                     no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_article_image()))

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    title = Column(TABLE_TYPES['name'], default='', nullable=False)
    subtitle = Column(TABLE_TYPES['subtitle'], default='', nullable=False)
    short = Column(TABLE_TYPES['text'], default='', nullable=False)
    long = Column(TABLE_TYPES['text'], default='', nullable=False)
    # long_stripped = Column(TABLE_TYPES['text'], nullable=False)

    keywords = Column(TABLE_TYPES['keywords'], nullable=False)
    author = Column(TABLE_TYPES['short_name'], nullable=False)

    status = Column(TABLE_TYPES['status'], default='NORMAL')
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    editor_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    editor = relationship(User, uselist=False)

    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Company.id))
    company = relationship(Company, uselist=False)

    publications = relationship('Publication', primaryjoin="Material.id==Publication.material_id",
                                cascade="save-update, merge, delete")

    image_galleries = relationship('MaterialImageGallery', cascade="all, delete-orphan")

    source_type = Column(TABLE_TYPES['string_30'])
    source_id = Column(TABLE_TYPES['string_100'])

    external_url = Column(TABLE_TYPES['string_1000'])

    # search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
    #                  'short': {'relevance': lambda field='short': RELEVANCE.short},
    #                  'long': {'relevance': lambda field='long': RELEVANCE.long},
    #                  'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}

    @validates('title', 'subtitle', 'keywords', 'author', 'source', 'external_url')
    def validate_code(self, key, value):
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[:max_len]
        return value


    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id,cr_tm,md_tm,external_url,company_id,illustration.url,title,subtitle,author,short,long,keywords,company.id|name',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    def validate(self, is_new):
        from .. import constants
        ret = super().validate(is_new, regexps={
            'title': r'.*[^\s]{3,}.*',
            'external_url': r'(^$)|(' +constants.REGEXP.URL + r')'
        })

        if not ret['errors'].get('external_url', None) and self.external_url != '':
            ret['warnings']['external_url'] = 'full text will be ignored if external url is provided'

        if ret['errors']:
            ret['errors']['_'] = 'You have some error'
        else:
            ret['notices']['_'] = 'Ok, you can click submit'

        return ret

    @staticmethod
    def subquery_company_materials(company_id=None, filters=None, sorts=None, source_type = None):
        sub_query = utils.db.query_filter(Material, company_id=company_id)
        if source_type is not None:
            sub_query = sub_query.filter_by(source_type = source_type)

        return sub_query

    def material_grid_row(self):
        ret = self.get_client_side_dict(fields='title,md_tm,editor.full_name,source_id,source_type,id,external_url,illustration.url')

        from sqlalchemy.sql import functions
        from ..models.company import NewsFeedCompany

        if ret['source_type'] == 'rss':
            rss_feed = NewsFeedCompany.get(ret['source_id'], True)
            ret['source_full_name'] = ('rss: ' + rss_feed.name) if rss_feed else 'rss'
        else:
            ret['source_full_name'] = ('user: ' + ret['editor']['full_name'])

        cnt = g.db.query(Publication.status, Publication.visibility,
                         functions.count(Publication.id).label('cnt')). \
            join(Material, and_(Publication.material_id == Material.id, Material.id == self.id)). \
            group_by(Publication.status, Publication.visibility).all()

        ret['publications'] = Publication.group_by_status_and_visibility(cnt)
        return ret

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def elastic_insert(self):
        pass

    def elastic_update(self):
        for p in self.publications:
            p.elastic_update()

    def elastic_delete(self):
        for p in self.publications:
            p.elastic_delete()


class ReaderPublication(Base, PRBase):
    __tablename__ = 'reader_publication'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    publication_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('publication.id'))
    favorite = Column(TABLE_TYPES['boolean'], default=False)
    liked = Column(TABLE_TYPES['boolean'], default=False)


class Publication(Base, PRBase, PRElasticDocument):
    __tablename__ = 'publication'
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)

    material_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('material.id'))
    material = relationship(Material, cascade="save-update, merge")

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    publishing_tm = Column(TABLE_TYPES['timestamp'])
    event_begin_tm = Column(TABLE_TYPES['timestamp'])
    event_end_tm = Column(TABLE_TYPES['timestamp'])

    read_count = Column(TABLE_TYPES['int'], default=0)
    like_count = Column(TABLE_TYPES['int'], default=0)

    tags = relationship(Tag, secondary='tag_publication', uselist=True,
                        order_by=lambda: expression.desc(TagPublication.position))

    status = Column(TABLE_TYPES['status'])

    STATUSES = {'SUBMITTED': 'SUBMITTED', 'UNPUBLISHED': 'UNPUBLISHED', 'PUBLISHED': 'PUBLISHED', 'DELETED': 'DELETED',
                'HOLDED': 'HOLDED'}

    def actions_by_portal(self):
        return []

    visibility = Column(TABLE_TYPES['status'], default='OPEN')
    VISIBILITIES = {'OPEN': 'OPEN', 'REGISTERED': 'REGISTERED', 'PAYED': 'PAYED'}

    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    portal_division = relationship('PortalDivision', uselist=False)

    company = relationship(Company, secondary='material',
                           primaryjoin="Publication.material_id == Material.id",
                           secondaryjoin="Material.company_id == Company.id",
                           viewonly=True, uselist=False)

    # elasticsearch begin
    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),

            'tags': PRElasticField(setter=lambda: ' '.join([t.text for t in self.tags])),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),

            'status': PRElasticField(setter=lambda: self.status, analyzed=False),

            'company_id': PRElasticField(analyzed=False, setter=lambda: self.material.company_id),
            'company_name': PRElasticField(setter=lambda: self.material.company_id),

            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.portal_division.portal_id),
            'portal_name': PRElasticField(setter=lambda: self.portal_division.portal.name),

            'division_id': PRElasticField(analyzed=False, setter=lambda: self.portal_division.id),
            'division_type': PRElasticField(analyzed=False,
                                            setter=lambda: self.portal_division.portal_division_type.id),
            'division_name': PRElasticField(setter=lambda: self.portal_division.get_url()),

            'date': PRElasticField(ftype='date', setter=lambda: int(self.publishing_tm.timestamp() * 1000)),

            'title': PRElasticField(setter=lambda: self.material.title, boost=10),
            'subtitle': PRElasticField(setter=lambda: self.strip_tags(self.material.subtitle), boost=5),
            'keywords': PRElasticField(setter=lambda: self.material.keywords, boost=5),
            'short': PRElasticField(setter=lambda: self.strip_tags(self.material.short), boost=2),
            'long': PRElasticField(setter=lambda: self.strip_tags(self.material.long)),

            'author': PRElasticField(setter=lambda: self.strip_tags(self.material.author)),
            'address': PRElasticField(setter=lambda: ''),

            'custom_data': PRElasticField(analyzed=False,
                                          setter=lambda: simplejson.dumps({'material_id': self.material_id})),

        }

    def elastic_get_index(self):
        return 'front'

    def elastic_get_doctype(self):
        return 'article'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def is_active(self):
        return True

    def create_article(self):
        ret = utils.dict_merge(
            self.get_client_side_dict(
                more_fields='portal_division.portal_division_type_id,portal_division.portal.logo.url'),
            Material.get(self.material_id).get_client_side_dict(
                fields='long|short|title|subtitle|keywords|illustration|author|external_url'),
            {'social_activity': self.social_activity_dict()},
            remove={'material': True})
        ret['portal_division']['url'] = PortalDivision.get(self.portal_division_id).get_url()
        return ret

    # def like_dislike_user_article(self, liked):
    #     article = db(ReaderPublication, publication_id=self.id,
    #                  user_id=g.user.id if g.user else None).one()
    #     article.favorite = True if liked else False
    #     self.like_count += 1

    def seo_dict(self):
        return {
            'title': self.material.title,
            'keywords': ','.join(t.text for t in self.tags),
            'description': self.material.short if self.material.short else self.material.subtitle,
            'image_url': self.material.illustration['url'] if self.material.illustration['selected_by_user'][
                                                                  'type'] == 'provenance' else None
        }

    @staticmethod
    def articles_visibility_for_user(portal_id):
        employer = True
        visibilities = Publication.VISIBILITIES.copy()
        if not utils.db.query_filter(UserCompany, user_id=getattr(g.user, 'id', None),
                                     status=UserCompany.STATUSES['EMPLOYMENT_ACTIVE']).filter(
                    UserCompany.company_id == utils.db.query_filter(Portal.company_owner_id, id=portal_id)).count():
            # visibilities.pop(Publication.VISIBILITIES['CONFIDENTIAL'])
            employer = False
        return visibilities.keys(), employer

    def article_visibility_details(self):
        # TODO: OZ by OZ: remove hardcded urls!
        actions = {Publication.VISIBILITIES['OPEN']: lambda: True,
                   Publication.VISIBILITIES['REGISTERED']:
                       lambda: True if getattr(g.user, 'id', False) else
                       dict(redirect_url='//' + Config.MAIN_DOMAIN + '/auth/login_signup',
                            message='This article can read only by users which are logged in.',
                            context='log in'),
                   Publication.VISIBILITIES['PAYED']: lambda:
                   dict(redirect_url='//' + Config.MAIN_DOMAIN + '/reader/buy_subscription',
                        message='This article can read only by users which bought subscription on this portal.',
                        context='buy subscription'),
                   # Publication.VISIBILITIES['CONFIDENTIAL']:
                   #     lambda portal_id=self.portal_division.portal.id: True if
                   #     Publication.articles_visibility_for_user(portal_id)[1] else
                   #     dict(redirect_url='//' + Config.MAIN_DOMAIN + '/auth/login_signup',
                   #          message='This article can read only employees of this company.',
                   #          context='login as employee')
                   }
        return actions[self.visibility]()

    def get_publisher_membership(self):
        from profapp.models.portal import MemberCompanyPortal
        return MemberCompanyPortal.get_by_portal_id_company_id(
            company_id=self.material.company_id, portal_id=self.portal_division.portal_id)

    def portal_publication_grid_row(self, actor_membership):
        from profapp.models.permissions import ActionsForPublicationAtMembership
        return {
            'id': self.id,
            'publication': self.get_client_side_dict(
                'id,status,visibility,publishing_tm,tags,portal_division.id|name,portal_division.portal.id|name|host,material.id|title|external_url'),
            'publisher_membership': self.get_publisher_membership().get_client_side_dict(
                fields='id,company.id|name|logo,portal.id|host|name|logo'),
            'actions': ActionsForPublicationAtMembership.actions(membership=actor_membership, publication=self)}

    def get_client_side_dict(self, fields='id|read_count|tags|portal_division_id|cr_tm|md_tm|status|material_id|'
                                          'visibility|publishing_tm|event_begin_tm,event_end_tm,company.id|name, '
                                          'portal_division.id|name|portal_id, portal_division.portal.id|name|host, material',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def group_by_status_and_visibility(cnt):
        ret = {'by_status_visibility': {s: {v: 0 for v in Publication.VISIBILITIES} for s in Publication.STATUSES},
               'by_visibility_status': {v: {s: 0 for s in Publication.STATUSES} for v in Publication.VISIBILITIES},
               'by_status': {s: 0 for s in Publication.STATUSES},
               'by_visibility': {s: 0 for s in Publication.VISIBILITIES},
               'all': 0,
               }

        for c in cnt:
            ret['by_status_visibility'][c.status][c.visibility] = c.cnt
            ret['by_status'][c.status] += c.cnt
            ret['by_visibility_status'][c.visibility][c.status] = c.cnt
            ret['by_visibility'][c.visibility] += c.cnt
            ret['all'] += c.cnt

        return ret

    @staticmethod
    def update_article_portal(publication_id, **kwargs):
        utils.db.query_filter(Publication, id=publication_id).update(kwargs)

    @staticmethod
    def subquery_portal_articles(portal_id, filters, sorts):
        sub_query = utils.db.query_filter(Publication)
        list_filters = []
        list_sorts = []
        if 'publication_status' in filters:
            list_filters.append(
                {'type': 'select', 'value': filters['publication_status'], 'field': Publication.status})
        if 'company' in filters:
            sub_query = sub_query.join(Publication.company)
            list_filters.append({'type': 'select', 'value': filters['company'], 'field': Company.id})
        if 'date' in filters:
            list_filters.append(
                {'type': 'date_range', 'value': filters['date'], 'field': Publication.publishing_tm})
        sub_query = sub_query. \
            join(Publication.portal_division). \
            join(PortalDivision.portal). \
            filter(Portal.id == portal_id)
        if 'title' in filters:
            list_filters.append({'type': 'text', 'value': filters['title'], 'field': Publication.title})
        if 'date' in sorts:
            list_sorts.append({'type': 'date', 'value': sorts['date'], 'field': Publication.publishing_tm})
        else:
            list_sorts.append({'type': 'date', 'value': 'desc', 'field': Publication.publishing_tm})
        sub_query = Grid.subquery_grid(sub_query, list_filters, list_sorts)
        return sub_query

    def position_unique_filter(self):
        return and_(Publication.portal_division_id == self.portal_division_id,
                    Publication.position != None)

    def validate(self, is_new):
        ret = super().validate(is_new)

        if not self.publishing_tm:
            ret['errors']['publishing_tm'] = 'Please select publication date'

        if not self.visibility in self.VISIBILITIES:
            ret['errors']['visibility'] = 'Please select publication visibility'

        if not self.portal_division_id and not self.portal_division:
            ret['errors']['portal_division_id'] = 'Please select portal division'
        else:
            portalDivision = PortalDivision.get(
                self.portal_division_id if self.portal_division_id else self.portal_division.id)
            if portalDivision.portal_division_type_id == 'events':
                if not self.event_begin_tm:
                    ret['errors']['event_begin_tm'] = 'Please select event start date'
                elif self.event_begin_tm and datetime.now() > self.event_begin_tm:
                    ret['warnings']['event_begin_tm'] = 'Event start time in past'

                if not self.event_end_tm:
                    ret['errors']['event_end_tm'] = 'Please select event end date'
                elif self.event_end_tm and self.event_begin_tm and self.event_begin_tm > self.event_end_tm:
                    ret['warnings']['event_end_tm'] = 'Event end time before event begin time'

        if ret['errors']:
            ret['errors']['_'] = 'You have some error'
        else:
            ret['notices']['_'] = 'Ok, you can click submit'

        return ret

    def set_tags_positions(self):
        tag_position = 0
        for tag in self.tags:
            tag_position += 1
            tag.position = tag_position
            # tag_pub = db(TagPublication).filter(and_(TagPublication.tag_id == tag.id,
            #                                          TagPublication.publication_id == self.id)).one()
            # tag_pub.position = tag_position
            # tag_pub.save()
        return self

    def get_related_articles(self, count=5):
        from sqlalchemy.sql import func

        return g.db().query(Publication).filter(
            and_(Publication.id != self.id,
                 Publication.portal_division_id.in_(
                     utils.db.query_filter(PortalDivision.id).filter(
                         PortalDivision.portal_id == self.portal_division.portal_id))
                 )).order_by(func.random()).limit(count).all()

    def add_to_read(self):
        if g.user and g.user.id:
            was_readed = utils.db.query_filter(ReaderPublication, user_id=g.user.id, publication_id=self.id).first()
            if not was_readed:
                was_readed = ReaderPublication(user_id=g.user.id, publication_id=self.id).save()
            return was_readed
        else:
            read = session.get('recently_read_articles', [])
            if self.id not in read:
                read.append(self.id)
                self.read_count += 1
                session['recently_read_articles'] = read
            return False

    def add_delete_favorite(self, favorite):
        reader_publication = self.add_to_read()
        reader_publication.favorite = True if favorite else False
        reader_publication.save()
        return self

    def add_delete_like(self, like):
        reader_publication = self.add_to_read()
        reader_publication.liked = True if like else False
        reader_publication.save()
        return self

    def is_favorite(self, user_id=None):
        return True if utils.db.query_filter(ReaderPublication,
                                             user_id=user_id if user_id else g.user.id if g.user else None,
                                             publication_id=self.id, favorite=True).first() else False

    def is_liked(self, user_id=None):
        return True if utils.db.query_filter(ReaderPublication,
                                             user_id=user_id if user_id else g.user.id if g.user else None,
                                             publication_id=self.id, liked=True).first() else False

    def liked_count(self):
        return utils.db.query_filter(ReaderPublication, publication_id=self.id, liked=True).count()

    def favorite_count(self):
        return utils.db.query_filter(ReaderPublication, publication_id=self.id, favorite=True).count()

    def social_activity_dict(self):
        return {
            'favorite': self.is_favorite(),
            'favorite_count': self.favorite_count(),
            'liked': self.is_liked(),
            'liked_count': self.liked_count()
        }
