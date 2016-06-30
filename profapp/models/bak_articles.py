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
from .files import FileImg
from .. import utils
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from .elastic import PRElasticField, PRElasticDocument, elasticsearch


class ArticlePortalDivision(Base, PRBase, PRElasticDocument):
    __tablename__ = 'article_portal_division'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    article_company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article_company.id'))
    # portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))
    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)

    cr_tm = Column(TABLE_TYPES['timestamp'])
    title = Column(TABLE_TYPES['name'], default='')
    subtitle = Column(TABLE_TYPES['subtitle'], default='')
    short = Column(TABLE_TYPES['text'], default='')
    long = Column(TABLE_TYPES['text'], default='')
    long_stripped = Column(TABLE_TYPES['text'], nullable=False)

    keywords = Column(TABLE_TYPES['keywords'], nullable=False)
    author = Column(TABLE_TYPES['short_name'], nullable=False)
    md_tm = Column(TABLE_TYPES['timestamp'])
    publishing_tm = Column(TABLE_TYPES['timestamp'])
    event_begin_tm = Column(TABLE_TYPES['timestamp'])
    event_end_tm = Column(TABLE_TYPES['timestamp'])
    position = Column(TABLE_TYPES['position'])
    read_count = Column(TABLE_TYPES['int'], default=0)

    tags = relationship(Tag, secondary='tag_publication', uselist=True)

    status = Column(TABLE_TYPES['status'], default='SUBMITTED')
    STATUSES = {'SUBMITTED': 'SUBMITTED', 'UNPUBLISHED': 'UNPUBLISHED', 'PUBLISHED': 'PUBLISHED', 'DELETED': 'DELETED'}

    visibility = Column(TABLE_TYPES['status'], default='OPEN')
    like_count = Column(TABLE_TYPES['int'], default=0)
    VISIBILITIES = {'OPEN': 'OPEN', 'REGISTERED': 'REGISTERED', 'PAYED': 'PAYED', 'CONFIDENTIAL': 'CONFIDENTIAL'}

    division = relationship('PortalDivision',
                            backref=backref('article_portal_division', cascade="save-update, merge, delete"),
                            cascade="save-update, merge, delete")

    company = relationship(Company, secondary='article_company',
                           primaryjoin="ArticlePortalDivision.article_company_id == ArticleCompany.id",
                           secondaryjoin="ArticleCompany.company_id == Company.id",
                           viewonly=True, uselist=False)

    # search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
    #                  'short': {'relevance': lambda field='short': RELEVANCE.short},
    #                  'long': {'relevance': lambda field='long': RELEVANCE.long},
    #                  'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}

    # elasticsearch begin
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

    # elasticsearch end


    def is_active(self):
        return True

    def check_favorite_status(self, user_id=None):
        return db(ReaderArticlePortalDivision, user_id=user_id if user_id else g.user.id if g.user else None,
                  article_portal_division_id=self.id,
                  favorite=True).count() > 0

    def check_liked_status(self, user_id=None):
        return db(ReaderArticlePortalDivision, user_id=user_id if user_id else g.user.id if g.user else None,
                  article_portal_division_id=self.id,
                  liked=True).count() > 0

    def check_liked_count(self):
        return db(ReaderArticlePortalDivision, article_portal_division_id=self.id, liked=True).count()

    def like_dislike_user_article(self, liked):
        article = db(ReaderArticlePortalDivision, article_portal_division_id=self.id,
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
        visibility = ArticlePortalDivision.visibility.in_(ArticlePortalDivision.articles_visibility_for_user(
            portal_id=division.portal_id)[0])
        filter = None
        if division_type == 'index':
            filter = {'class': ArticlePortalDivision,
                      'filter': and_(ArticlePortalDivision.portal_division_id.in_(db(
                          PortalDivision.id, portal_id=division.portal_id).filter(
                          PortalDivision.portal_division_type_id != 'events'
                      )), ArticlePortalDivision.status == ArticlePortalDivision.STATUSES['PUBLISHED'], visibility),
                      'return_fields': 'default_dict', 'tags': True}
        elif division_type == 'news':
            if not company_id:
                filter = {'class': ArticlePortalDivision,
                          'filter': and_(ArticlePortalDivision.portal_division_id == division_id,
                                         ArticlePortalDivision.status ==
                                         ArticlePortalDivision.STATUSES['PUBLISHED'], visibility),
                          'return_fields': 'default_dict', 'tags': True}
            else:
                filter = {'class': ArticlePortalDivision,
                          'filter': and_(ArticlePortalDivision.portal_division_id == division_id,
                                         ArticlePortalDivision.status ==
                                         ArticlePortalDivision.STATUSES['PUBLISHED'],
                                         db(ArticleCompany, company_id=company_id,
                                            id=ArticlePortalDivision.article_company_id).exists(), visibility),
                          'return_fields': 'default_dict', 'tags': True}
        elif division_type == 'events':
            if not company_id:
                filter = {'class': ArticlePortalDivision,
                          'filter': and_(ArticlePortalDivision.portal_division_id == division_id,
                                         ArticlePortalDivision.status ==
                                         ArticlePortalDivision.STATUSES['PUBLISHED'], visibility),
                          'return_fields': 'default_dict', 'tags': True}
            else:
                filter = {'class': ArticlePortalDivision,
                          'filter': and_(ArticlePortalDivision.portal_division_id == division_id,
                                         ArticlePortalDivision.status ==
                                         ArticlePortalDivision.STATUSES['PUBLISHED'],
                                         db(ArticleCompany, company_id=company_id,
                                            id=ArticlePortalDivision.article_company_id).exists(), visibility),
                          'return_fields': 'default_dict', 'tags': True}
        return filter

    def add_recently_read_articles_to_session(self):
        if self.id not in session.get('recently_read_articles', []):
            self.read_count += 1
        session['recently_read_articles'] = list(
            filter(bool, set(session.get('recently_read_articles', []) + [self.id])))

    portal = relationship('Portal',
                          secondary='portal_division',
                          primaryjoin="ArticlePortalDivision.portal_division_id == PortalDivision.id",
                          secondaryjoin="PortalDivision.portal_id == Portal.id",
                          back_populates='publications',
                          uselist=False)

    def __init__(self, article_company_id=None, title=None, short=None, keywords=None, position=None,
                 long=None, status=None, portal_division_id=None, image_file_id=None, subtitle=None,
                 like_count=None):
        self.article_company_id = article_company_id
        self.title = title
        self.subtitle = subtitle
        self.short = short
        self.keywords = keywords
        self.image_file_id = image_file_id
        self.long = long
        self.status = status
        self.position = position
        self.portal_division_id = portal_division_id
        self.like_count = like_count
        # self.portal_id = portal_id



    @staticmethod
    def articles_visibility_for_user(portal_id):
        employer = True
        visibilities = ArticlePortalDivision.VISIBILITIES.copy()
        if not db(UserCompany, user_id=getattr(g.user, 'id', None),
                  status=UserCompany.STATUSES['ACTIVE']).filter(
                    UserCompany.company_id == db(Portal.company_owner_id, id=portal_id)).count():
            visibilities.pop(ArticlePortalDivision.VISIBILITIES['CONFIDENTIAL'])
            employer = False
        return visibilities.keys(), employer

    def article_visibility_details(self):
        actions = {ArticlePortalDivision.VISIBILITIES['OPEN']: lambda: True,
                   ArticlePortalDivision.VISIBILITIES['REGISTERED']:
                       lambda: True if getattr(g.user, 'id', False) else
                       dict(redirect_url='//profireader.com/auth/login_signup',
                            message='This article can read only by users which are logged in.',
                            context='log in'),
                   ArticlePortalDivision.VISIBILITIES['PAYED']: lambda:
                   dict(redirect_url='//profireader.com/reader/buy_subscription',
                        message='This article can read only by users which bought subscription on this portal.',
                        context='buy subscription'),
                   ArticlePortalDivision.VISIBILITIES['CONFIDENTIAL']:
                       lambda portal_id=self.portal.id: True if
                       ArticlePortalDivision.articles_visibility_for_user(portal_id)[1] else
                       dict(redirect_url='//profireader.com/auth/login_signup',
                            message='This article can read only employees of this company.',
                            context='login as employee')
                   }
        return actions[self.visibility]()

    def get_client_side_dict(self, fields='id|image_file_id|read_count|title|subtitle|short|long_stripped|tags|author|'
                                          'portal_division_id|image_file_id|position|keywords|cr_tm|md_tm|status|'
                                          'visibility|publishing_tm|event_begin_tm,event_end_tm,company.id|name, '
                                          'division.id|'
                                          'name|portal_id, portal.id|name|host',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    @staticmethod
    def update_article_portal(article_portal_division_id, **kwargs):
        db(ArticlePortalDivision, id=article_portal_division_id).update(kwargs)

    @staticmethod
    def get_portals_where_company_send_article(company_id):

        # return db(ArticlePortalDivision, company_id=company_id).group_by.all()

        # all = {'name': 'All', 'id': 0}
        portals = {}
        # portals['0'] = {'name': 'All'}
        # portals.append(all)

        for article in db(ArticleCompany, company_id=company_id).all():
            for port in article.portal_article:
                portals[port.portal.id] = port.portal.name
        return portals

    @staticmethod
    def get_companies_which_send_article_to_portal(portal_id):
        # all = {'name': 'All', 'id': 0}
        companies = {}
        # companies.append(all)
        articles = g.db.query(ArticlePortalDivision). \
            join(ArticlePortalDivision.portal). \
            filter(Portal.id == portal_id).all()
        # for article in db(ArticlePortalDivision, portal_id=portal_id).all():
        for article in articles:
            companies[article.company.id] = article.company.name
        return companies

    # TODO: SS by OZ: contition `if datetime(*localtime[:6]) > article['publishing_tm']:` should be checked by sql (passed
    # to search function)
    @staticmethod
    def get_list_reader_articles(articles):
        list_articles = []
        for article_id, article in articles.items():
            article['tags'] = [tag.get_client_side_dict() for tag in article['tags']]
            article['is_favorite'] = ReaderArticlePortalDivision.article_is_favorite(g.user.id, article_id)
            article['liked'] = ReaderArticlePortalDivision.count_likes(g.user.id, article_id)
            article['list_liked_reader'] = ReaderArticlePortalDivision.get_list_reader_liked(article_id)
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
        sub_query = db(ArticlePortalDivision)
        list_filters = []
        list_sorts = []
        if 'publication_status' in filters:
            list_filters.append(
                {'type': 'select', 'value': filters['publication_status'], 'field': ArticlePortalDivision.status})
        if 'company' in filters:
            sub_query = sub_query.join(ArticlePortalDivision.company)
            list_filters.append({'type': 'select', 'value': filters['company'], 'field': Company.id})
        if 'date' in filters:
            list_filters.append(
                {'type': 'date_range', 'value': filters['date'], 'field': ArticlePortalDivision.publishing_tm})
        sub_query = sub_query. \
            join(ArticlePortalDivision.division). \
            join(PortalDivision.portal). \
            filter(Portal.id == portal_id)
        if 'title' in filters:
            list_filters.append({'type': 'text', 'value': filters['title'], 'field': ArticlePortalDivision.title})
        if 'date' in sorts:
            list_sorts.append({'type': 'date', 'value': sorts['date'], 'field': ArticlePortalDivision.publishing_tm})
        else:
            list_sorts.append({'type': 'date', 'value': 'desc', 'field': ArticlePortalDivision.publishing_tm})
        sub_query = Grid.subquery_grid(sub_query, list_filters, list_sorts)
        return sub_query


    def position_unique_filter(self):
        return and_(ArticlePortalDivision.portal_division_id == self.portal_division_id,
                    ArticlePortalDivision.position != None)

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

    def get_image_client_side_dict(self):
        return Article.get_image_client_side_dict(self)

    def set_image_client_side_dict(self, client_data):
        return Article.set_image_client_side_dict(self, client_data)

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


class ArticleCompany(Base, PRBase):
    __tablename__ = 'article_company'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    editor_user_id = Column(TABLE_TYPES['id_profireader'],
                            ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))
    article_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article.id'))
    # created_from_version_id = Column(TABLE_TYPES['id_profireader'],
    # ForeignKey('article_version.id'))
    title = Column(TABLE_TYPES['title'], nullable=False)
    subtitle = Column(TABLE_TYPES['subtitle'], default='')
    short = Column(TABLE_TYPES['text'], nullable=False)
    long = Column(TABLE_TYPES['text'], nullable=False)
    long_stripped = Column(TABLE_TYPES['text'], nullable=False)

    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    status = Column(TABLE_TYPES['status'], default='NORMAL')
    STATUSES = {'NORMAL': 'NORMAL', 'EDITING': 'EDITING', 'FINISHED': 'FINISHED', 'DELETED': 'DELETED',
                'APPROVED': 'APPROVED'}

    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)
    keywords = Column(TABLE_TYPES['keywords'], nullable=False)
    # TODO: OZ by OZ: we need keywords in ArticleCompany ??

    company = relationship(Company)
    editor = relationship(User)
    article = relationship('Article', primaryjoin="and_(Article.id==ArticleCompany.article_id)",
                           uselist=False)
    portal_article = relationship('ArticlePortalDivision',
                                  primaryjoin="ArticleCompany.id=="
                                              "ArticlePortalDivision."
                                              "article_company_id",
                                  backref='company_article')

    search_fields = {'title': {'relevance': lambda field='title': RELEVANCE.title},
                     'short': {'relevance': lambda field='short': RELEVANCE.short},
                     'subtitle': {'relevance': lambda field='subtitle': RELEVANCE.short},
                     'long': {'relevance': lambda field='long': RELEVANCE.long},
                     'keywords': {'relevance': lambda field='keywords': RELEVANCE.keywords}}

    def is_active(self):
        return True

    def get_client_side_dict(self,
                             fields='id|title|subtitle|short|keywords|cr_tm|md_tm|article_id|image_file_id|company_id',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    def get_image_client_side_dict(self):
        return Article.get_image_client_side_dict(self)

    def set_image_client_side_dict(self, client_data):
        return Article.set_image_client_side_dict(self, client_data)

    def validate(self, is_new):
        ret = super().validate(is_new)
        if not re.match('.*\S{2}.*', self.title, re.IGNORECASE):
            ret['errors']['title'] = 'pls enter tite longer than 2 letters'
        if not re.match('\S+.*', self.keywords, re.IGNORECASE):
            ret['warnings']['keywords'] = 'pls enter at least one keyword'
        return ret

    @staticmethod
    def get_companies_where_user_send_article(user_id):
        # all = {'name': 'All', 'id': 0}
        # companies = []
        # companies.append(all)
        companies = {}
        for article in db(Article, author_user_id=user_id).all():
            for comp in article.submitted_versions:
                companies[comp.company.id] = comp.company.name
                # companies.append(comp.company.get_client_side_dict(fields='id, name'))
        return companies  # all, [dict(comp) for comp in set([tuple(c.items()) for c in companies])]

    @staticmethod
    def get_companies_for_article(article_id):
        companies = []
        for article in db(Article, id=article_id).all():
            for comp in article.submitted_versions:
                companies.append(comp.company.get_client_side_dict(fields='id, name'))
        return [dict(comp) for comp in set([tuple(c.items()) for c in companies])]

    # def clone_for_company(self, company_id):
    #     return self.detach().attr({'company_id': company_id,
    #                                'status': ARTICLE_STATUS_IN_COMPANY.
    #                               submitted})

    @staticmethod
    def subquery_user_articles(search_text=None, user_id=None, **kwargs):
        own_article = aliased(ArticleCompany, name="OwnArticle")
        sub_query = db(Article, own_article.md_tm, author_user_id=user_id). \
            join(own_article,
                 and_(Article.id == own_article.article_id, own_article.company_id == None))
        article_filter = db(ArticleCompany, article_id=Article.id)
        if 'title' in search_text:
            article_filter = article_filter.filter(ArticleCompany.title.ilike(
                "%" + repr(search_text['title']).strip("'") + "%"))
        if 'company' in kwargs['filter'].keys():
            article_filter = article_filter.filter(ArticleCompany.company_id == kwargs['filter']['company'])
        if 'status' in kwargs['filter'].keys():
            article_filter = article_filter.filter(ArticleCompany.status == kwargs['filter']['status'])
        if 'date' in kwargs['sort'].keys():
            sub_query = sub_query.order_by(own_article.md_tm.asc()) if kwargs['sort'][
                                                                           'date'] == 'asc' else sub_query.order_by(
                own_article.md_tm.desc())
        else:
            sub_query = sub_query.order_by(own_article.md_tm.desc())
        return sub_query.filter(article_filter.exists())


    @staticmethod
    def subquery_company_materials(company_id=None, filters=None, sorts=None):
        sub_query = db(ArticleCompany, company_id=company_id)
        list_filters = []
        list_sorts = []
        if 'status' in filters or 'portal.name' in filters:
            sub_query = sub_query.join(ArticlePortalDivision,
                                       ArticlePortalDivision.article_company_id == ArticleCompany.id)
            if 'status' in filters:
                list_filters.append({'type': 'multiselect', 'value': filters['status'],
                                     'field': ArticlePortalDivision.status})
            if 'portal.name' in filters:
                sub_query = sub_query.join(PortalDivision,
                                           PortalDivision.id == ArticlePortalDivision.portal_division_id).join(Portal,
                                                                                                               Portal.id == PortalDivision.portal_id)
                list_filters.append({'type': 'multiselect', 'value': filters['portal.name'], 'field': Portal.name})
        if 'md_tm' in filters:
            list_filters.append({'type': 'date_range', 'value': filters['md_tm'], 'field': ArticleCompany.md_tm})
        if 'title' in filters:
            list_filters.append({'type': 'text', 'value': filters['title_author'], 'field': ArticleCompany.title})
        if 'title&editor.profireader_name' in filters:
            sub_query = sub_query.join(User,
                                       User.id == ArticleCompany.editor_user_id)
            list_filters.append({'type': 'text_multi', 'value': filters['title&editor.profireader_name'],
                                 'field': [ArticleCompany.title, User.profireader_name]})
        if 'editor.profireader_name' in filters:
            sub_query = sub_query.join(User,
                                       User.id == ArticleCompany.editor_user_id)
            list_filters.append(
                {'type': 'text', 'value': filters['editor.profireader_name'], 'field': User.profireader_name})
        if 'md_tm' in sorts:
            list_sorts.append({'type': 'date', 'value': sorts['md_tm'], 'field': ArticleCompany.md_tm})
        else:
            list_sorts.append({'type': 'date', 'value': 'desc', 'field': ArticleCompany.md_tm})
        sub_query = Grid.subquery_grid(sub_query, list_filters, list_sorts)
        return sub_query

        # self.portal_devision_id = portal_devision_id
        # self.article_company_id = article_company_id
        # self.title = title
        # self.short = short
        # self.long = long
        # self.status = status

    # def find_files_used(self):
    #     ret = [found.group(1) for found in re.findall('http://file001.profireader.com/([^/]*)/', self.long)]
    #     # if self.image_file_id:
    #     #     ret.append(self.image_file_id)
    #     return ret

    def clone_for_portal_images_and_replace_urls(self, portal_division_id, article_portal_division):
        filesintext = {found[1]: True for found in
                       re.findall('(https?://file001.profireader.com/([^/]*)/)', self.long)}
        if self.image_file_id:
            filesintext[self.image_file_id] = True
        company = db(PortalDivision, id=portal_division_id).one().portal.own_company

        for file_id in filesintext:
            filesintext[file_id] = \
                File.get(file_id).copy_from_cropped_file().id

        if self.image_file_id:
            article_portal_division.image_file_id = filesintext[self.image_file_id]

        article_portal_division.save()

        long_text = self.long
        for old_image_id in filesintext:
            long_text = long_text.replace('://file001.profireader.com/%s/' % (old_image_id,),
                                          '://file001.profireader.com/%s/' % (filesintext[old_image_id],))
        return long_text


    def get_article_owner_portal(self, **kwargs):
        return [art_port_div.division.portal for art_port_div in self.portal_article if kwargs][0]

    @staticmethod
    def update_article(company_id, article_id, **kwargs):
        db(ArticleCompany, company_id=company_id, id=article_id).update(kwargs)


def set_long_striped(mapper, connection, target):
    target.long_stripped = MLStripper().strip_tags(target.long)


event.listen(ArticlePortalDivision, 'before_update', set_long_striped)
event.listen(ArticlePortalDivision, 'before_insert', set_long_striped)
event.listen(ArticleCompany, 'before_update', set_long_striped)
event.listen(ArticleCompany, 'before_insert', set_long_striped)


class Article(Base, PRBase):
    __tablename__ = 'article'

    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    author_user_id = Column(TABLE_TYPES['id_profireader'],
                            ForeignKey('user.id'), nullable=False)

    submitted_versions = relationship(ArticleCompany,
                                      primaryjoin="and_(Article.id==ArticleCompany.article_id, "
                                                  "ArticleCompany.company_id!=None)")

    mine_version = relationship(ArticleCompany,
                                primaryjoin="and_(Article.id==ArticleCompany.article_id, "
                                            "ArticleCompany.company_id==None)",
                                uselist=False)

    def get_client_side_dict(self,
                             fields='id, mine_version|submitted_versions.id|title|short|'
                                    'cr_tm|md_tm|company_id|status|image_file_id, '
                                    'submitted_versions.editor.id|'
                                    'profireader_name, '
                                    'submitted_versions.company.name',
                             more_fields=None):
        return self.to_dict(fields, more_fields)

    def get_article_with_html_tag(self, text_into_html):
        article = self.get_client_side_dict()
        article['mine_version']['title'] = article['mine_version']['title'].replace(text_into_html,
                                                                                    '<span class=colored>%s</span>' % text_into_html)
        return article

    @staticmethod
    def search_for_company_to_submit(user_id, article_id, searchtext):
        # TODO: AA by OZ:    .filter(user_id has to be employee in company and
        # TODO: must have rights to submit article to this company)
        return [x.get_client_side_dict(fields='id,name') for x in db(Company).filter(~db(ArticleCompany).
                                                                                     filter_by(company_id=Company.id,
                                                                                               article_id=article_id).
                                                                                     exists()).filter(
            Company.name.ilike("%" + searchtext + "%")).all()]

    @staticmethod
    def save_edited_version(user_id, article_company_id, **kwargs):
        a = ArticleCompany.get(article_company_id)
        return a.attr(kwargs)

    @staticmethod
    def get_articles_for_user(user_id):
        return g.db.query(Article).filter_by(author_user_id=user_id).all()

    # @staticmethod
    # def subquery_articles_at_portal(portal_division_id=None, search_text=None):
    #
    #     if not search_text:
    #         sub_query = db(ArticlePortalDivision).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ArticlePortalDivision.STATUSES['PUBLISHED'])
    #     else:
    #         sub_query = db(ArticlePortalDivision).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ArticlePortalDivision.STATUSES['PUBLISHED']).filter(
    #             or_(
    #                 ArticlePortalDivision.title.ilike("%" + search_text + "%"),
    #                 ArticlePortalDivision.short.ilike("%" + search_text + "%"),
    #                 ArticlePortalDivision.long.ilike("%" + search_text + "%")))
    #     return sub_query

    @staticmethod
    def subquery_articles_at_portal(search_text=None, **kwargs):
        portal_id = None
        if 'portal_id' in kwargs.keys():
            portal_id = kwargs['portal_id']
            kwargs.pop('portal_id', None)
        # search_text = 'aa'
        # test = db(Search).filter(Search.text.ilike("%" + search_text + "%")).filter(
        #     Search.index == db(ArticlePortalDivision).filter(
        #         ArticlePortalDivision.portal_division_id == db(
        #             PortalDivision, portal_id=portal_id).first().id).first()).all()
        # for a in test:
        #     print(a)
        # print(**kwargs)
        # test = db(Search, table_name=ArticlePortalDivision.__tablename__).filter(Search.text.ilike("%" + search_text + "%")).filter(
        #     ArticlePortalDivision.portal_division_id in db(PortalDivision.id, portal_id=portal_id).all())
        # for a in test:
        #     print(a.text)

        sub_query = db(ArticlePortalDivision, status=ArticlePortalDivision.STATUSES['PUBLISHED'], **kwargs). \
            order_by(ArticlePortalDivision.publishing_tm.desc()).filter(
            text(' "publishing_tm" < clock_timestamp() '))

        if portal_id:
            sub_query = sub_query.join(PortalDivision).join(Portal).filter(Portal.id == portal_id)

        if search_text:
            sub_query = sub_query. \
                filter(or_(ArticlePortalDivision.title.ilike("%" + search_text + "%"),
                           ArticlePortalDivision.short.ilike("%" + search_text + "%"),
                           ArticlePortalDivision.long_stripped.ilike("%" + search_text + "%")))
        return sub_query

    @staticmethod
    def logo_file_properties(article):
        noimage_url = utils.fileUrl(FOLDER_AND_FILE.no_article_image())
        return {
            'browse': article.id,
            'upload': True,
            'none': noimage_url,
            'crop': True,
            'image_size': [600, 480],
            'min_size': [100, 80],
            'aspect_ratio': [300 / 240., 300 / 240.],
            'preset_urls': {},
            'no_selection_url': noimage_url
        }

    @staticmethod
    def get_image_client_side_dict(article):
        return article.get_image_cropped_file(Article.image_cropping_properties(article),
                                              db(FileImg, croped_image_id=article.image_file_id).first())

    @staticmethod
    def set_image_client_side_dict(article, client_data):
        if client_data['selected_by_user']['type'] == 'preset':
            client_data['selected_by_user'] = {'type': 'none'}
        if not article.company:
            folder_id = Company.get(article.company_id).system_folder_file_id
        else:
            folder_id = article.company.system_folder_file_id
        article.image_file_id = article.set_image_cropped_file(Article.logo_file_properties(article),
                                                               client_data, article.image_file_id, folder_id)
        return article

    # @staticmethod
    # def get_articles_for_portal(page_size, portal_division_id,
    #                             pages, page=1, search_text=None):
    #     page -= 1
    #     if not search_text:
    #         query = g.db.query(ArticlePortalDivision).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ArticlePortalDivision.STATUSES['PUBLISHED'])
    #     else:
    #         query = g.db.query(ArticlePortalDivision).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ArticlePortalDivision.STATUSES['PUBLISHED']).filter(
    #             or_(
    #                 ArticlePortalDivision.title.ilike("%" + search_text + "%"),
    #                 ArticlePortalDivision.short.ilike("%" + search_text + "%"),
    #                 ArticlePortalDivision.long.ilike("%" + search_text + "%")))
    #
    #     if page_size:
    #         query = query.limit(page_size)
    #     if page:
    #         query = query.offset(page*page_size) if int(page) in range(
    #             0, int(pages)) else query.offset(pages*page_size)
    #
    #     return query

    @staticmethod
    def get_articles_submitted_to_company(company_id):
        articles = g.db.query(ArticleCompany).filter_by(company_id=company_id).all()
        return articles if articles else []

    @staticmethod
    def get_material_grid_data(material):
        from ..models.rights import PublishUnpublishInPortal
        dict = material.get_client_side_dict(fields='md_tm,title,editor.profireader_name,id')
        dict.update({'portal.name': None if len(material.portal_article) == 0 else '', 'level': True})
        dict.update({'actions': None if len(material.portal_article) == 0 else '', 'level': True})
        list = [utils.dict_merge(
            article_portal.get_client_side_dict(fields='portal.name|host,status, id, portal_division_id'),
            {'actions':
                 {'edit': PublishUnpublishInPortal(publication=article_portal,
                                                   division=article_portal.division, company=material.company)
                     .actions()[PublishUnpublishInPortal.ACTIONS['EDIT']]
                  } if article_portal.status != 'SUBMITTED' and article_portal.status != "DELETED" else {}
             })
                for article_portal in material.portal_article]
        return dict, list

        # for article in articles:
        #     article.possible_new_statuses = ARTICLE_STATUS_IN_COMPANY.\
        #         can_user_change_status_to(article.status)


class ArticleCompanyHistory(Base, PRBase):
    __tablename__ = 'article_company_history'
    id = Column(TABLE_TYPES['bigint'], primary_key=True)
    editor_user_id = Column(TABLE_TYPES['id_profireader'])
    company_id = Column(TABLE_TYPES['id_profireader'])
    name = Column(TABLE_TYPES['name'])
    short = Column(TABLE_TYPES['text'], default='')
    long = Column(TABLE_TYPES['text'], default='')
    article_company_id = Column(TABLE_TYPES['id_profireader'])
    article_id = Column(TABLE_TYPES['id_profireader'])

    def __init__(self, editor_user_id=None, company_id=None, name=None,
                 short=None, long=None, article_company_id=None,
                 article_id=None):
        super(ArticleCompanyHistory, self).__init__()
        self.editor_user_id = editor_user_id
        self.company_id = company_id
        self.name = name
        self.short = short
        self.long = long
        self.article_company_id = article_company_id
        self.article_id = article_id


class ReaderArticlePortalDivision(Base, PRBase):
    __tablename__ = 'reader_article_portal_division'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    article_portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article_portal_division.id'))
    favorite = Column(TABLE_TYPES['boolean'], default=False)
    liked = Column(TABLE_TYPES['boolean'], default=False)

    def __init__(self, user_id=None, article_portal_division_id=None, favorite=False, liked=False):
        super(ReaderArticlePortalDivision, self).__init__()
        self.user_id = user_id
        self.article_portal_division_id = article_portal_division_id
        self.favorite = favorite
        self.liked = liked

    @staticmethod
    def add_delete_favorite_user_article(article_portal_division_id, favorite):
        articleReader = db(ReaderArticlePortalDivision, article_portal_division_id=article_portal_division_id,
                           user_id=g.user.id).first()
        if not articleReader:
            articleReader = ReaderArticlePortalDivision.add_to_table_if_not_exists(article_portal_division_id)
        articleReader.favorite = True if favorite else False
        articleReader.save()
        return articleReader.favorite

    @staticmethod
    def add_delete_liked_user_article(article_portal_division_id, liked):
        articleReader = db(ReaderArticlePortalDivision, article_portal_division_id=article_portal_division_id,
                           user_id=g.user.id).first()

        if not articleReader:
            articleReader = ReaderArticlePortalDivision.add_to_table_if_not_exists(article_portal_division_id)
        articleReader.liked = False if articleReader.liked else True
        article_division = ArticlePortalDivision.get(article_portal_division_id)
        article_division.like_count = article_division.like_count - 1 \
            if articleReader.liked == False and article_division.like_count != 0 else article_division.like_count + 1
        article_division.save()
        articleReader.save()
        return articleReader.liked

    @staticmethod
    def count_likes(user_id, article_portal_division_id):
        article_division = ArticlePortalDivision.get(article_portal_division_id)
        return article_division.like_count

    @staticmethod
    def article_is_liked(user_id, article_portal_division_id):
        reader_article = db(ReaderArticlePortalDivision, user_id=user_id,
                            article_portal_division_id=article_portal_division_id).first()
        return reader_article.liked if reader_article else False

    @staticmethod
    def article_is_favorite(user_id, article_portal_division_id):
        reader_article = db(ReaderArticlePortalDivision, user_id=user_id,
                            article_portal_division_id=article_portal_division_id).first()
        return reader_article.favorite if reader_article else False

    @staticmethod
    def get_list_reader_liked(article_portal_division_id):
        me = db(ReaderArticlePortalDivision, article_portal_division_id=article_portal_division_id, user_id=g.user.id,
                liked=True).first()
        limit = 15
        articles = db(ReaderArticlePortalDivision, article_portal_division_id=article_portal_division_id, liked=True)
        liked_users = [User.get(article.user_id).profireader_name for article in articles.limit(limit)]
        if me:
            if g.user.profireader_name in liked_users:
                index = liked_users.index(g.user.profireader_name)
                del liked_users[index]
            else:
                del liked_users[-1]
            liked_users.insert(0, g.user.profireader_name)
        if articles.count() > limit:
            liked_users.append('and ' + str((articles.count() - limit)) + ' more...')
        return liked_users

    @staticmethod
    def add_to_table_if_not_exists(article_portal_division_id):
        if not db(ReaderArticlePortalDivision,
                  user_id=g.user.id, article_portal_division_id=article_portal_division_id).count():
            return ReaderArticlePortalDivision(user_id=g.user.id,
                                               article_portal_division_id=article_portal_division_id,
                                               favorite=False).save()

    def get_article_portal_division(self):
        return db(ArticlePortalDivision, id=self.article_portal_division_id).one()

    @staticmethod
    def subquery_favorite_articles():
        return db(ArticlePortalDivision).filter(
            ArticlePortalDivision.id == db(ReaderArticlePortalDivision,
                                           user_id=g.user.id,
                                           favorite=True).subquery().c.article_portal_division_id)

    def get_portal_division(self):
        return db(PortalDivision).filter(PortalDivision.id == db(ArticlePortalDivision,
                                                                 id=self.article_portal_division_id).c.portal_division_id).one()
