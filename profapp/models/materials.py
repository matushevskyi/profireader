from sqlalchemy import Column, ForeignKey, text
from sqlalchemy.orm import relationship, aliased, backref
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..models.company import Company, UserCompany
from ..models.portal import PortalDivision, Portal
from ..models.users import User
from ..models.files import File
from ..models.tag import Tag, TagPortalDivision, TagPublication
from .pr_base import PRBase, Base, MLStripper, Grid
from utils.db_utils import db
from flask import g, session
from sqlalchemy.sql import or_, and_
import re
from sqlalchemy import event
from ..constants.SEARCH import RELEVANCE
from datetime import datetime
from .files import FileImg, FileImgCropProperties
from .. import utils
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from .elastic import PRElasticField, PRElasticDocument, elasticsearch
from sqlalchemy.ext.associationproxy import association_proxy


class FileImgProxy:
    browse = True
    upload = True
    crop = True
    image_size = [600, 600]
    min_size = [60, 60]
    aspect_ratio = [0.1, 10]
    preset_urls = {}
    # none = utils.fileUrl(FOLDER_AND_FILE.no_image())
    no_selection_url = utils.fileUrl(FOLDER_AND_FILE.no_image())

    def __init__(self, browse=None, upload=None, crop=None, image_size=None, min_size=None,
                 aspect_ratio=None, preset_urls=None, no_selection_url=None):
        if browse is not None:
            self.browse = browse
        if upload is not None:
            self.upload = upload
        if crop is not None:
            self.crop = crop
        if image_size is not None:
            self.image_size = image_size
        if min_size is not None:
            self.min_size = min_size
        if aspect_ratio is not None:
            self.aspect_ratio = aspect_ratio
        if preset_urls is not None:
            self.preset_urls = preset_urls
        if no_selection_url is not None:
            self.no_selection_url = no_selection_url

    def proxy_getter(self, obj):
        return {
            'url': utils.fileUrl(obj.provenance_image_file_id) if obj else self.no_selection_url,
            'selected_by_user': {'type': 'provenance',
                                 'crop': obj.get_client_side_dict(),
                                 'provenance_file_id': obj.provenance_image_file_id
                                 } if obj else {'type': 'none'},
            'cropper': {
                'browse': self.browse,
                'upload': self.upload,
                'crop': self.crop,
                'image_size': self.image_size,
                'min_size': self.min_size,
                'aspect_ratio': self.aspect_ratio,
                'preset_urls': self.preset_urls,
                'no_selection_url': self.no_selection_url
            }}

    def proxy_setter(self, obj, value):
        print((obj, value))
        return None

    def get_factory(self, *args, **kwargs):
        return self.proxy_getter, self.proxy_setter

    def get_proxy(self, target_collection):
        return association_proxy(target_collection, None, getset_factory=self.get_factory)


class Material(Base, PRBase):
    __tablename__ = 'material'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    # portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))

    # TODO: OZ by OZ: remove me
    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=True)

    illustration_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    illustration_file_img = relationship(FileImg, uselist=False)

    # illustration = image_file_association_proxy('illustration_file_img', 'illustration',
    #                                             getset_factory=image_file_association_proxy)

    illustration = FileImgProxy(image_size=[600, 480],
                                min_size=[600 / 6, 480 / 6],
                                aspect_ratio=[600 / 480., 600 / 480.],
                                # none=utils.fileUrl(FOLDER_AND_FILE.no_article_image()),
                                no_selection_url=utils.fileUrl(FOLDER_AND_FILE.no_article_image())).get_proxy(
        'illustration_file_img')

    # illustration_file_img_properties =

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    title = Column(TABLE_TYPES['name'], default='', nullable=False)
    subtitle = Column(TABLE_TYPES['subtitle'], default='', nullable=False)
    short = Column(TABLE_TYPES['text'], default='', nullable=False)
    long = Column(TABLE_TYPES['text'], default='', nullable=False)
    long_stripped = Column(TABLE_TYPES['text'], nullable=False)

    keywords = Column(TABLE_TYPES['keywords'], nullable=False)
    author = Column(TABLE_TYPES['short_name'], nullable=False)

    status = Column(TABLE_TYPES['status'], default='NORMAL')
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    editor_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    editor = relationship(User, uselist=False)

    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Company.id))
    company = relationship(Company, uselist=False)

    publications = relationship('Publication', primaryjoin="Material.id==Publication.material_id")

    search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
                     'short': {'relevance': lambda field='short': RELEVANCE.short},
                     'long': {'relevance': lambda field='long': RELEVANCE.long},
                     'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}

    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),
            'title': PRElasticField(setter=lambda: self.title, boost=10),
            'author': PRElasticField(setter=lambda: self.author, boost=10),
            'subtitle': PRElasticField(setter=lambda: self.subtitle, boost=4),
            'keywords': PRElasticField(setter=lambda: self.keywords, boost=3),
            'short': PRElasticField(setter=lambda: self.short, boost=2),
            'long': PRElasticField(setter=lambda: self.long),
            'tags': PRElasticField(analyzed=False, setter=lambda: ' '.join([t.text for t in self.tags])),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),
            'date': PRElasticField(ftype='date', setter=lambda: int(self.publishing_tm.timestamp() * 1000)),
            'user': PRElasticField(analyzed=False),
            'user_id': PRElasticField(analyzed=False),
            'portal': PRElasticField(setter=lambda: self.portal.name),
            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.portal.id),
            'division': PRElasticField(setter=lambda: self.division.name),
            'portal_division_id': PRElasticField(analyzed=False, setter=lambda: self.division.id)
        }

    def elastic_get_index(self):
        return 'articles'

    def elastic_get_doctype(self):
        return 'articles'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def elastic_remove_all_indexes(cls):
        return elasticsearch.remove_index('articles')

    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id,cr_tm,md_tm,company_id,illustration_file_img,title,subtitle,author,short,keywords,company.id|name',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    def validate(self, is_new):
        ret = super().validate(is_new)
        if (self.omit_validation):
            return ret

        if ret['errors']:
            ret['errors']['_'] = 'You have some error'
        else:
            ret['notices']['_'] = 'Ok, you can click submit'

        return ret

    @staticmethod
    def after_insert(mapper=None, connection=None, target=None):
        pass

    @staticmethod
    def after_update(mapper=None, connection=None, target=None):
        # target.elastic_replace()
        pass

    @staticmethod
    def after_delete(mapper=None, connection=None, target=None):
        pass

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, 'after_insert', cls.after_insert)
        event.listen(cls, 'after_update', cls.after_update)
        event.listen(cls, 'after_delete', cls.after_delete)

    @staticmethod
    def subquery_company_materials(company_id=None, filters=None, sorts=None):
        sub_query = db(Material, company_id=company_id)
        return sub_query

    @staticmethod
    def get_material_grid_data(material):
        from ..models.rights import PublishUnpublishInPortal
        dict = material.get_client_side_dict(fields='md_tm,title,editor.profireader_name,id,illustration.url')
        dict.update({'portal.name': None if len(material.publications) == 0 else '', 'level': True})
        dict.update({'actions': None if len(material.publications) == 0 else '', 'level': True})
        list = [utils.dict_merge(
            publication.get_client_side_dict(fields='portal.name|host,status, id, portal_division_id'),
            {'actions':
                 {'edit': PublishUnpublishInPortal(publication=publication,
                                                   division=publication.division, company=material.company)
                     .actions()[PublishUnpublishInPortal.ACTIONS['EDIT']]
                  } if publication.status != 'SUBMITTED' and publication.status != "DELETED" else {}
             })
                for publication in material.publications]
        return dict, list

    @staticmethod
    def get_portals_where_company_send_article(company_id):
        portals = {}

        for m in db(Material, company_id=company_id).all():
            for pub in m.publications:
                portals[pub.portal.id] = pub.portal.name
        return portals

    @staticmethod
    def get_companies_which_send_article_to_portal(portal_id):
        # all = {'name': 'All', 'id': 0}
        companies = {}
        # companies.append(all)
        articles = g.db.query(Publication). \
            join(Publication.portal). \
            filter(Portal.id == portal_id).all()
        # for article in db(Publication, portal_id=portal_id).all():
        for article in articles:
            companies[article.company.id] = article.company.name
        return companies

    def set_image_client_side_dict(self, client_data):
        if client_data['selected_by_user']['type'] == 'preset':
            client_data['selected_by_user'] = {'type': 'none'}
        if not self.company:
            folder_id = Company.get(self.company_id).system_folder_file_id
        else:
            folder_id = self.company.system_folder_file_id

        FileImg.set_image_cropped_file(self.illustration_image_cropped, self.image_cropping_properties(),
                                       client_data, folder_id)
        return self


def set_long_striped(mapper, connection, target):
    target.long_stripped = MLStripper().strip_tags(target.long)


event.listen(Material, 'before_update', set_long_striped)
event.listen(Material, 'before_insert', set_long_striped)


class Publication(Base, PRBase, PRElasticDocument):
    __tablename__ = 'publication'
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))

    material_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('material.id'))
    material = relationship('Material', cascade="save-update, merge, delete")

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    publishing_tm = Column(TABLE_TYPES['timestamp'])
    event_begin_tm = Column(TABLE_TYPES['timestamp'])
    event_end_tm = Column(TABLE_TYPES['timestamp'])

    read_count = Column(TABLE_TYPES['int'], default=0)
    like_count = Column(TABLE_TYPES['int'], default=0)

    tags = relationship(Tag, secondary='tag_publication', uselist=True)

    status = Column(TABLE_TYPES['status'], default='SUBMITTED')
    STATUSES = {'SUBMITTED': 'SUBMITTED', 'UNPUBLISHED': 'UNPUBLISHED', 'PUBLISHED': 'PUBLISHED', 'DELETED': 'DELETED'}

    visibility = Column(TABLE_TYPES['status'], default='OPEN')
    VISIBILITIES = {'OPEN': 'OPEN', 'REGISTERED': 'REGISTERED', 'PAYED': 'PAYED', 'CONFIDENTIAL': 'CONFIDENTIAL'}

    division = relationship('PortalDivision', backref=backref('article_portal_division'),
                            cascade="save-update, merge, delete")

    company = relationship(Company, secondary='material',
                           primaryjoin="Publication.material_id == Material.id",
                           secondaryjoin="Material.company_id == Company.id",
                           viewonly=True, uselist=False)

    search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
                     'short': {'relevance': lambda field='short': RELEVANCE.short},
                     'long': {'relevance': lambda field='long': RELEVANCE.long},
                     'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}

    # elasticsearch begin
    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),
            'tags': PRElasticField(analyzed=False, setter=lambda: ' '.join([t.text for t in self.tags])),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),
            'date': PRElasticField(ftype='date', setter=lambda: int(self.publishing_tm.timestamp() * 1000)),
            'user': PRElasticField(analyzed=False),
            'user_id': PRElasticField(analyzed=False),
            'portal': PRElasticField(setter=lambda: self.portal.name),
            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.portal.id),
            'division': PRElasticField(setter=lambda: self.division.name),
            'portal_division_id': PRElasticField(analyzed=False, setter=lambda: self.division.id)
        }

    def elastic_get_index(self):
        return 'articles'

    def elastic_get_doctype(self):
        return 'articles'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def elastic_remove_all_indexes(cls):
        return elasticsearch.remove_index('articles')

    # elasticsearch end


    def is_active(self):
        return True

    def check_favorite_status(self, user_id=None):
        return db(ReaderPublication, user_id=user_id if user_id else g.user.id if g.user else None,
                  article_portal_division_id=self.id,
                  favorite=True).count() > 0

    def check_liked_status(self, user_id=None):
        return db(ReaderPublication, user_id=user_id if user_id else g.user.id if g.user else None,
                  article_portal_division_id=self.id,
                  liked=True).count() > 0

    def check_liked_count(self):
        return db(ReaderPublication, article_portal_division_id=self.id, liked=True).count()

    def like_dislike_user_article(self, liked):
        article = db(ReaderPublication, article_portal_division_id=self.id,
                     user_id=g.user.id if g.user else None).one()
        article.favorite = True if liked else False
        self.like_count += 1

    def search_filter_default(self, division_id, company_id=None):
        """ :param division_id: string with id from table portal_division,
                   optional company_id: string with id from table company. If provided
                   , this function will check if ArticleCompany has relation with our class.
            :return: dict with prepared filter parameters for search method """
        division = db(PortalDivision, id=division_id).one()
        division_type = division.portal_division_type.id
        visibility = Publication.visibility.in_(Publication.articles_visibility_for_user(
            portal_id=division.portal_id)[0])
        filter = None
        if division_type == 'index':
            filter = {'class': Publication,
                      'filter': and_(Publication.portal_division_id.in_(db(
                          PortalDivision.id, portal_id=division.portal_id).filter(
                          PortalDivision.portal_division_type_id != 'events'
                      )), Publication.status == Publication.STATUSES['PUBLISHED'], visibility),
                      'return_fields': 'default_dict', 'tags': True}
        elif division_type == 'news':
            if not company_id:
                filter = {'class': Publication,
                          'filter': and_(Publication.portal_division_id == division_id,
                                         Publication.status ==
                                         Publication.STATUSES['PUBLISHED'], visibility),
                          'return_fields': 'default_dict', 'tags': True}
            else:
                filter = {'class': Publication,
                          'filter': and_(Publication.portal_division_id == division_id,
                                         Publication.status ==
                                         Publication.STATUSES['PUBLISHED'],
                                         db(ArticleCompany, company_id=company_id,
                                            id=Publication.article_company_id).exists(), visibility),
                          'return_fields': 'default_dict', 'tags': True}
        elif division_type == 'events':
            if not company_id:
                filter = {'class': Publication,
                          'filter': and_(Publication.portal_division_id == division_id,
                                         Publication.status ==
                                         Publication.STATUSES['PUBLISHED'], visibility),
                          'return_fields': 'default_dict', 'tags': True}
            else:
                filter = {'class': Publication,
                          'filter': and_(Publication.portal_division_id == division_id,
                                         Publication.status ==
                                         Publication.STATUSES['PUBLISHED'],
                                         db(ArticleCompany, company_id=company_id,
                                            id=Publication.article_company_id).exists(), visibility),
                          'return_fields': 'default_dict', 'tags': True}
        return filter

    def add_recently_read_articles_to_session(self):
        if self.id not in session.get('recently_read_articles', []):
            self.read_count += 1
        session['recently_read_articles'] = list(
            filter(bool, set(session.get('recently_read_articles', []) + [self.id])))

    portal = relationship('Portal',
                          secondary='portal_division',
                          primaryjoin="Publication.portal_division_id == PortalDivision.id",
                          secondaryjoin="PortalDivision.portal_id == Portal.id",
                          back_populates='publications',
                          uselist=False)

    @staticmethod
    def articles_visibility_for_user(portal_id):
        employer = True
        visibilities = Publication.VISIBILITIES.copy()
        if not db(UserCompany, user_id=getattr(g.user, 'id', None),
                  status=UserCompany.STATUSES['ACTIVE']).filter(
                    UserCompany.company_id == db(Portal.company_owner_id, id=portal_id)).count():
            visibilities.pop(Publication.VISIBILITIES['CONFIDENTIAL'])
            employer = False
        return visibilities.keys(), employer

    def article_visibility_details(self):
        actions = {Publication.VISIBILITIES['OPEN']: lambda: True,
                   Publication.VISIBILITIES['REGISTERED']:
                       lambda: True if getattr(g.user, 'id', False) else
                       dict(redirect_url='//profireader.com/auth/login_signup',
                            message='This article can read only by users which are logged in.',
                            context='log in'),
                   Publication.VISIBILITIES['PAYED']: lambda:
                   dict(redirect_url='//profireader.com/reader/buy_subscription',
                        message='This article can read only by users which bought subscription on this portal.',
                        context='buy subscription'),
                   Publication.VISIBILITIES['CONFIDENTIAL']:
                       lambda portal_id=self.portal.id: True if
                       Publication.articles_visibility_for_user(portal_id)[1] else
                       dict(redirect_url='//profireader.com/auth/login_signup',
                            message='This article can read only employees of this company.',
                            context='login as employee')
                   }
        return actions[self.visibility]()

    def get_client_side_dict(self, fields='id|read_count|tags|portal_division_id|cr_tm|md_tm|status|'
                                          'visibility|publishing_tm|event_begin_tm,event_end_tm,company.id|name, '
                                          'division.id|name|portal_id, portal.id|name|host, material',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def update_article_portal(article_portal_division_id, **kwargs):
        db(Publication, id=article_portal_division_id).update(kwargs)

    # TODO: SS by OZ: contition `if datetime(*localtime[:6]) > article['publishing_tm']:` should be checked by sql (passed
    # to search function)
    @staticmethod
    def get_list_reader_articles(articles):
        list_articles = []
        for article_id, article in articles.items():
            article['tags'] = [tag.get_client_side_dict() for tag in article['tags']]
            article['is_favorite'] = ReaderPublication.article_is_favorite(g.user.id, article_id)
            article['liked'] = ReaderPublication.count_likes(g.user.id, article_id)
            article['list_liked_reader'] = ReaderPublication.get_list_reader_liked(article_id)
            article['company']['logo'] = File().get(articles[article_id]['company']['logo_file_id']).url() if \
                articles[article_id]['company']['logo_file_id'] else utils.fileUrl(FOLDER_AND_FILE.no_company_logo())
            article['portal']['logo'] = File().get(articles[article_id]['portal']['logo_file_id']).url() if \
                articles[article_id]['portal']['logo_file_id'] else utils.fileUrl(FOLDER_AND_FILE.no_company_logo())
            del articles[article_id]['company']['logo_file_id'], articles[article_id]['portal']['logo_file_id']
            list_articles.append(article)
        return list_articles

    # def clone_for_company(self, company_id):
    #     return self.detach().attr({'company_id': company_id,
    #                                'status': ARTICLE_STATUS_IN_COMPANY.
    #                               submitted})

    @staticmethod
    def subquery_portal_articles(portal_id, filters, sorts):
        sub_query = db(Publication)
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
            join(Publication.division). \
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
        if (self.omit_validation):
            return ret

        if not self.publishing_tm:
            ret['errors']['publishing_tm'] = 'Please select publication date'

        if not self.portal_division_id:
            ret['errors']['portal_division_id'] = 'Please select portal division'
        else:
            portalDivision = PortalDivision.get(self.portal_division_id)
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
            tag_pub = db(TagPublication).filter(and_(TagPublication.tag_id == tag.id,
                                                     TagPublication.article_portal_division_id == self.id)).one()
            tag_pub.position = tag_position
            tag_pub.save()
        return self

    @staticmethod
    def after_insert(mapper=None, connection=None, target=None):
        pass

    @staticmethod
    def after_update(mapper=None, connection=None, target=None):
        target.elastic_replace()
        pass

    @staticmethod
    def after_delete(mapper=None, connection=None, target=None):
        pass

    @classmethod
    def __declare_last__(cls):
        event.listen(cls, 'after_insert', cls.after_insert)
        event.listen(cls, 'after_update', cls.after_update)
        event.listen(cls, 'after_delete', cls.after_delete)
