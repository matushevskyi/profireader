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
from flask import g, session, app, current_app
from sqlalchemy.sql import or_, and_
import re
from sqlalchemy import event
from ..constants.SEARCH import RELEVANCE
from datetime import datetime
from .files import FileImg, FileImgDescriptor
from .. import utils
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from .elastic import PRElasticField, PRElasticDocument
from config import Config


class Material(Base, PRBase, PRElasticDocument):
    __tablename__ = 'material'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    # portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))

    # TODO: OZ by OZ: remove me
    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=True)

    illustration_file_img_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(FileImg.id), nullable=True)
    illustration_file_img = relationship(FileImg, uselist=False)

    illustration = FileImgDescriptor(relation_name='illustration_file_img',
                                     file_decorator=lambda m, r, f: f.attr(
                                         name='%s_for_material_illustration_%s' % (f.name, m.id),
                                         parent_id=m.company.system_folder_file_id,
                                         root_folder_id=m.company.system_folder_file_id),
                                     image_size=[600, 480],
                                     min_size=[600 / 6, 480 / 6],
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

    publications = relationship('Publication', primaryjoin="Material.id==Publication.material_id")

    # search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
    #                  'short': {'relevance': lambda field='short': RELEVANCE.short},
    #                  'long': {'relevance': lambda field='long': RELEVANCE.long},
    #                  'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}


    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id,cr_tm,md_tm,company_id,illustration.url,title,subtitle,author,short,keywords,company.id|name',
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
    def subquery_company_materials(company_id=None, filters=None, sorts=None):
        sub_query = db(Material, company_id=company_id)
        return sub_query

    @staticmethod
    def get_material_grid_data(material):
        from ..models.rights import PublishUnpublishInPortal
        dict = material.get_client_side_dict(fields='md_tm,title,editor.full_name,id,illustration.url')
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

        # def set_image_client_side_dict(self, client_data):
        #     if client_data['selected_by_user']['type'] == 'preset':
        #         client_data['selected_by_user'] = {'type': 'none'}
        #     if not self.company:
        #         folder_id = Company.get(self.company_id).system_folder_file_id
        #     else:
        #         folder_id = self.company.system_folder_file_id
        #
        #     FileImg.set_image_cropped_file(self.illustration_image_cropped, self.image_cropping_properties(),
        #                                    client_data, folder_id)
        #     return self

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

    division = relationship('PortalDivision', cascade="save-update, delete")

    portal = relationship('Portal',
                          secondary='portal_division',
                          primaryjoin="Publication.portal_division_id == PortalDivision.id",
                          secondaryjoin="PortalDivision.portal_id == Portal.id",
                          back_populates='publications',
                          uselist=False)

    company = relationship(Company, secondary='material',
                           primaryjoin="Publication.material_id == Material.id",
                           secondaryjoin="Material.company_id == Company.id",
                           viewonly=True, uselist=False)

    # elasticsearch begin
    def elastic_get_fields(self):
        return {
            'id': PRElasticField(analyzed=False, setter=lambda: self.id),
            'tags': PRElasticField(analyzed=False, setter=lambda: ' '.join([t.text for t in self.tags]), boost=5),
            'tag_ids': PRElasticField(analyzed=False, setter=lambda: [t.id for t in self.tags]),
            'date': PRElasticField(ftype='date', setter=lambda: int(self.publishing_tm.timestamp() * 1000)),
            'user': PRElasticField(analyzed=False, setter=lambda: ''),
            'status': PRElasticField(setter=lambda: self.status, analyzed=False),
            'user_id': PRElasticField(analyzed=False, setter=lambda: ''),
            'publisher_company_id': PRElasticField(analyzed=False, setter=lambda: self.material.company_id),
            'material_id': PRElasticField(analyzed=False, setter=lambda: self.material_id),
            'portal': PRElasticField(setter=lambda: self.division.portal.name),
            'long': PRElasticField(setter=lambda: self.strip_tags(self.material.long)),
            'author': PRElasticField(setter=lambda: self.strip_tags(self.material.author)),
            'short': PRElasticField(setter=lambda: self.strip_tags(self.material.short), boost=2),
            'subtitle': PRElasticField(setter=lambda: self.strip_tags(self.material.subtitle), boost=5),
            'title': PRElasticField(setter=lambda: self.material.title, boost=10),
            'portal_id': PRElasticField(analyzed=False, setter=lambda: self.division.portal_id),
            'division': PRElasticField(setter=lambda: self.division.name, boost=2),
            'portal_division_id': PRElasticField(analyzed=False, setter=lambda: self.division.id)
        }

    def elastic_get_index(self):
        return 'publications'

    def elastic_get_doctype(self):
        return 'publications'

    def elastic_get_id(self):
        return self.id

    @classmethod
    def __declare_last__(cls):
        cls.elastic_listeners(cls)

    def is_active(self):
        return True

    def check_favorite_status(self, user_id=None):
        return db(ReaderPublication, user_id=user_id if user_id else g.user.id if g.user else None,
                  publication_id=self.id,
                  favorite=True).count() > 0

    def check_liked_status(self, user_id=None):
        return db(ReaderPublication, user_id=user_id if user_id else g.user.id if g.user else None,
                  publication_id=self.id,
                  liked=True).count() > 0

    def check_liked_count(self):
        return db(ReaderPublication, publication_id=self.id, liked=True).count()

    def create_article(self):
        return utils.dict_merge(
            self.get_client_side_dict(more_fields='division.portal_division_type_id,portal.logo.url'),
            Material.get(self.material_id).get_client_side_dict(
                fields='long|short|title|subtitle|keywords|illustration'), remove={'material': True})

    def like_dislike_user_article(self, liked):
        article = db(ReaderPublication, publication_id=self.id,
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
        # TODO: OZ by OZ: remove hardcided urls!
        actions = {Publication.VISIBILITIES['OPEN']: lambda: True,
                   Publication.VISIBILITIES['REGISTERED']:
                       lambda: True if getattr(g.user, 'id', False) else
                       dict(redirect_url='//'+Config.MAIN_DOMAIN+'/auth/login_signup',
                            message='This article can read only by users which are logged in.',
                            context='log in'),
                   Publication.VISIBILITIES['PAYED']: lambda:
                   dict(redirect_url='//'+Config.MAIN_DOMAIN+'/reader/buy_subscription',
                        message='This article can read only by users which bought subscription on this portal.',
                        context='buy subscription'),
                   Publication.VISIBILITIES['CONFIDENTIAL']:
                       lambda portal_id=self.portal.id: True if
                       Publication.articles_visibility_for_user(portal_id)[1] else
                       dict(redirect_url='//'+Config.MAIN_DOMAIN+'/auth/login_signup',
                            message='This article can read only employees of this company.',
                            context='login as employee')
                   }
        return actions[self.visibility]()

    def get_client_side_dict(self, fields='id|read_count|tags|portal_division_id|cr_tm|md_tm|status|material_id|'
                                          'visibility|publishing_tm|event_begin_tm,event_end_tm,company.id|name, '
                                          'division.id|name|portal_id, portal.id|name|host, material',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def update_article_portal(publication_id, **kwargs):
        db(Publication, id=publication_id).update(kwargs)

    # # TODO: SS by OZ: contition `if datetime(*localtime[:6]) > article['publishing_tm']:` should be checked by sql (passed
    # # to search function)
    # @staticmethod
    # def get_list_reader_articles(articles):
    #     list_articles = []
    #     for article_id, article in articles.items():
    #         article['tags'] = [tag.get_client_side_dict() for tag in article['tags']]
    #         article['is_favorite'] = ReaderPublication.article_is_favorite(g.user.id, article_id)
    #         article['liked'] = ReaderPublication.count_likes(g.user.id, article_id)
    #         article['list_liked_reader'] = ReaderPublication.get_list_reader_liked(article_id)
    #         article['company']['logo'] = Company.get(articles[article_id]['company']['id']).logo.url
    #         article['portal']['logo'] = File().get(articles[article_id]['portal']['logo_file_id']).url() if \
    #             articles[article_id]['portal']['logo_file_id'] else utils.fileUrl(FOLDER_AND_FILE.no_company_logo())
    #         # del articles[article_id]['company']['logo_file_id'], articles[article_id]['portal']['logo_file_id']
    #         list_articles.append(article)
    #     return list_articles

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

        if not self.portal_division_id and not self.division:
            ret['errors']['portal_division_id'] = 'Please select portal division'
        else:
            portalDivision = PortalDivision.get(self.portal_division_id if self.portal_division_id else self.division.id)
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
                     db(PortalDivision.id).filter(PortalDivision.portal_id == self.division.portal_id))
                 )).order_by(func.random()).limit(count).all()


class ReaderPublication(Base, PRBase):
    __tablename__ = 'reader_publication'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    publication_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('publication.id'))
    favorite = Column(TABLE_TYPES['boolean'], default=False)
    liked = Column(TABLE_TYPES['boolean'], default=False)

    def __init__(self, user_id=None, publication_id=None, favorite=False, liked=False):
        super(ReaderPublication, self).__init__()
        self.user_id = user_id
        self.publication_id = publication_id
        self.favorite = favorite
        self.liked = liked

    @staticmethod
    def add_delete_favorite_user_article(publication_id, favorite):
        articleReader = db(ReaderPublication, publication_id=publication_id,
                           user_id=g.user.id).first()
        if not articleReader:
            articleReader = ReaderPublication.add_to_table_if_not_exists(publication_id)
        articleReader.favorite = True if favorite else False
        articleReader.save()
        return articleReader.favorite

    @staticmethod
    def add_delete_liked_user_article(publication_id, liked):
        articleReader = db(ReaderPublication, publication_id=publication_id,
                           user_id=g.user.id).first()

        if not articleReader:
            articleReader = ReaderPublication.add_to_table_if_not_exists(publication_id)
        articleReader.liked = False if articleReader.liked else True
        article_division = ArticlePortalDivision.get(publication_id)
        article_division.like_count = article_division.like_count - 1 \
            if articleReader.liked == False and article_division.like_count != 0 else article_division.like_count + 1
        article_division.save()
        articleReader.save()
        return articleReader.liked

    @staticmethod
    def count_likes(user_id, publication_id):
        article_division = ArticlePortalDivision.get(publication_id)
        return article_division.like_count

    @staticmethod
    def article_is_liked(user_id, publication_id):
        reader_article = db(ReaderPublication, user_id=user_id,
                            publication_id=publication_id).first()
        return reader_article.liked if reader_article else False

    @staticmethod
    def article_is_favorite(user_id, publication_id):
        reader_article = db(ReaderPublication, user_id=user_id,
                            publication_id=publication_id).first()
        return reader_article.favorite if reader_article else False

    @staticmethod
    def get_list_reader_liked(publication_id):
        me = db(ReaderPublication, publication_id=publication_id, user_id=g.user.id,
                liked=True).first()
        limit = 15
        articles = db(ReaderPublication, publication_id=publication_id, liked=True)
        liked_users = [User.get(article.user_id).full_name for article in articles.limit(limit)]
        if me:
            if g.user.full_name in liked_users:
                index = liked_users.index(g.user.full_name)
                del liked_users[index]
            else:
                del liked_users[-1]
            liked_users.insert(0, g.user.full_name)
        if articles.count() > limit:
            liked_users.append('and ' + str((articles.count() - limit)) + ' more...')
        return liked_users

    @staticmethod
    def add_to_table_if_not_exists(publication_id):
        if not db(ReaderPublication,
                  user_id=g.user.id, publication_id=publication_id).count():
            return ReaderPublication(user_id=g.user.id,
                                     publication_id=publication_id,
                                     favorite=False).save()

    def get_article_portal_division(self):
        return db(ArticlePortalDivision, id=self.publication_id).one()

    @staticmethod
    def subquery_favorite_articles():
        return db(ArticlePortalDivision).filter(
            ArticlePortalDivision.id == db(ReaderPublication,
                                           user_id=g.user.id,
                                           favorite=True).subquery().c.publication_id)

    def get_portal_division(self):
        return db(PortalDivision).filter(PortalDivision.id == db(ArticlePortalDivision,
                                                                 id=self.publication_id).c.portal_division_id).one()


