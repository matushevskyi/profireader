from sqlalchemy import Column, ForeignKey, text
from sqlalchemy.orm import relationship
from ..constants.TABLE_TYPES import TABLE_TYPES
# from db_init import db_session
from ..models.company import Company
from ..models.portal import PortalDivision, Portal
from ..models.users import User
from ..models.files import File, FileContent
#from ..models.tag import Tag

from utils.db_utils import db
from .pr_base import PRBase, Base
# from db_init import Base
from utils.db_utils import db
from ..constants.ARTICLE_STATUSES import ARTICLE_STATUS_IN_COMPANY, ARTICLE_STATUS_IN_PORTAL
from flask import g
from sqlalchemy.sql import or_
import re
from sqlalchemy import event
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
    def strip_tags(self, html):
        self.feed(html)
        return self.get_data()


class ArticlePortal(Base, PRBase):
    __tablename__ = 'article_portal'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    # TODO (AA asks):
    # TODO: 1) isn't it better to have columns portal_division_id and article_id
    # TODO: instead of article_company_id and portal_id and portal_division_id?
    # TODO: 2) having portal_division_id do we really need column portal_id?
    article_company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article_company.id'))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id'))
    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'))

    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)

    cr_tm = Column(TABLE_TYPES['timestamp'])
    title = Column(TABLE_TYPES['name'], default='')
    short = Column(TABLE_TYPES['text'], default='')
    long = Column(TABLE_TYPES['text'], default='')
    long_stripped = Column(TABLE_TYPES['text'], nullable=False)
    keywords = Column(TABLE_TYPES['keywords'], nullable=False)
    md_tm = Column(TABLE_TYPES['timestamp'])
    publishing_tm = Column(TABLE_TYPES['timestamp'])
    status = Column(TABLE_TYPES['id_profireader'], default=ARTICLE_STATUS_IN_PORTAL.published)

    portal_division = relationship('PortalDivision', backref='article_portal')
    company = relationship(Company, secondary='article_company',
                           primaryjoin="ArticlePortal.article_company_id == ArticleCompany.id",
                           secondaryjoin="ArticleCompany.company_id == Company.id",
                           viewonly=True, uselist=False)
    article_portal_tags = relationship('TagPortalDivision', secondary='tag_portal_division_article',
                                       back_populates='articles', lazy='dynamic')

    # main_tag = relationship(Tag, secondary='tag_portal_division',
    #                         primaryjoin="ArticlePortal.main_tag_id == TagPortalDivisionArticle.id",
    #                         secondaryjoin="TagPortalDivisionArticle.tag_portal_division_id == "
    #                                       ".id",
    #                         viewonly=True, uselist=False)

    def __init__(self, article_company_id=None, title=None, short=None, keywords=None,
                 long=None, status=None, portal_division_id=None, image_file_id=None,
                 portal_id=None):
        self.article_company_id = article_company_id
        self.title = title
        self.short = short
        self.keywords = keywords
        self.image_file_id = image_file_id
        self.long = long
        self.status = status
        self.portal_division_id = portal_division_id
        self.portal_id = portal_id


    def get_client_side_dict(self, fields='id|image_file_id|title|short|image_file_id|'
                                          'long|keywords|cr_tm|md_tm|'
                                          'status|publishing_tm, '
                                          'company.id|name, division.id|name'):
        return self.to_dict(fields)

    @staticmethod
    def update_article_portal(article_portal_id, **kwargs):
        db(ArticlePortal, id=article_portal_id).update(kwargs)


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
    short = Column(TABLE_TYPES['text'], nullable=False)
    long = Column(TABLE_TYPES['text'], nullable=False)
    long_stripped = Column(TABLE_TYPES['text'], nullable=False)
    status = Column(TABLE_TYPES['status'], nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])
    image_file_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), nullable=False)
    keywords = Column(TABLE_TYPES['keywords'], nullable=False)

    company = relationship(Company)
    editor = relationship(User)
    article = relationship('Article', primaryjoin="and_(Article.id==ArticleCompany.article_id)",
                           uselist=False)
    portal_article = relationship('ArticlePortal',
                                  primaryjoin="ArticleCompany.id=="
                                              "ArticlePortal."
                                              "article_company_id",
                                  backref='company_article')

    def get_client_side_dict(self, fields='id|title|short|'
                                          'long|keywords|cr_tm|md_tm|company_id|'
                                          'article_id|image_file_id|'
                                          'status, company.name'):
        return self.to_dict(fields)
    
    def clone_for_company(self, company_id):
        return self.detach().attr({'company_id': company_id,
                                   'status': ARTICLE_STATUS_IN_COMPANY.
                                  submitted})

        # self.portal_devision_id = portal_devision_id
        # self.article_company_id = article_company_id
        # self.title = title
        # self.short = short
        # self.long = long
        # self.status = status

    # def find_files_used(self):
    #     ret = [found.group(1) for found in re.findall('http://file001.profi.ntaxa.com/([^/]*)/', self.long)]
    #     # if self.image_file_id:
    #     #     ret.append(self.image_file_id)
    #     return ret

    def clone_for_portal(self, division_id):

        filesintext = {found[1]:True for found in re.findall('(http://file001.profi.ntaxa.com/([^/]*)/)', self.long)}
        if self.image_file_id:
            filesintext[self.image_file_id] = True
        company = db(PortalDivision, id=division_id).one().portal.own_company



        article_portal = ArticlePortal(title=self.title, short=self.short, long=self.long,
                           portal_division_id=division_id,
                           article_company_id=self.id,
                           keywords=self.keywords,
                           portal_id=db(PortalDivision, id=division_id).one().portal_id).save()

        for file_id in filesintext:
            filesintext[file_id] = \
                File.get(file_id).copy_file(company_id=company.id, parent_folder_id=company.system_folder_file_id, article_portal_id=article_portal.id).save().id

        if self.image_file_id:
            article_portal.image_file_id = filesintext[self.image_file_id]

        long_text = self.long
        for old_image_id in filesintext:
            long_text = long_text.replace('http://file001.profi.ntaxa.com/%s/' % (old_image_id, ),
                                          'http://file001.profi.ntaxa.com/%s/' % (filesintext[old_image_id], ))

        article_portal.long = long_text

        self.portal_article.append(article_portal)

        return self


    def get_article_owner_portal(self, **kwargs):
        return [art_port.division.portal for art_port in self.portal_article if kwargs][0]

    @staticmethod
    def update_article(company_id, article_id, **kwargs):
        db(ArticleCompany, company_id=company_id, id=article_id).update(
            kwargs)


@event.listens_for(ArticlePortal, 'before_insert')
@event.listens_for(ArticlePortal, 'before_update')
@event.listens_for(ArticleCompany, 'before_insert')
@event.listens_for(ArticleCompany, 'before_update')
def set_long_striped(mapper, connection, target):
        target.long_stripped = MLStripper().strip_tags(target.long)

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
                                    'submitted_versions.company.name'):
        return self.to_dict(fields)

    @staticmethod
    def save_new_article(user_id, **kwargs):
        return Article(mine_version=ArticleCompany(editor_user_id=user_id,
                                           company_id=None,
                                           **kwargs),
                                           author_user_id=user_id)

    @staticmethod
    def search_for_company_to_submit(user_id, article_id, searchtext):
        # TODO: AA by OZ:    .filter(user_id has to be employee in company and
        # TODO: must have rights to submit article to this company)
        return [x.to_dict('id,name') for x in db(Company)
                .filter(~db(ArticleCompany).
                        filter_by(company_id=Company.id,
                        article_id=article_id).exists())
                .filter(Company.name.ilike(
                        "%" + searchtext + "%")).all()]

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
    #         sub_query = db(ArticlePortal).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ARTICLE_STATUS_IN_PORTAL.published)
    #     else:
    #         sub_query = db(ArticlePortal).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ARTICLE_STATUS_IN_PORTAL.published).filter(
    #             or_(
    #                 ArticlePortal.title.ilike("%" + search_text + "%"),
    #                 ArticlePortal.short.ilike("%" + search_text + "%"),
    #                 ArticlePortal.long.ilike("%" + search_text + "%")))
    #     return sub_query

    @staticmethod
    def subquery_articles_at_portal(search_text=None, **kwargs):

        if not search_text:
            sub_query = db(ArticlePortal, status=ARTICLE_STATUS_IN_PORTAL.published, **kwargs).\
                order_by('publishing_tm').filter(text(' "publishing_tm" < clock_timestamp() '))
        else:
            sub_query = db(ArticlePortal, status=ARTICLE_STATUS_IN_PORTAL.published, **kwargs).\
                order_by('publishing_tm').filter(text(' "publishing_tm" < clock_timestamp() ')).\
                filter(or_(
                    ArticlePortal.title.ilike("%" + search_text + "%"),
                    ArticlePortal.short.ilike("%" + search_text + "%"),
                    ArticlePortal.long.ilike("%" + search_text + "%")))
        return sub_query

    # @staticmethod
    # def get_articles_for_portal(page_size, portal_division_id,
    #                             pages, page=1, search_text=None):
    #     page -= 1
    #     if not search_text:
    #         query = g.db.query(ArticlePortal).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ARTICLE_STATUS_IN_PORTAL.published)
    #     else:
    #         query = g.db.query(ArticlePortal).order_by('publishing_tm').filter(text(
    #             ' "publishing_tm" < clock_timestamp() ')).filter_by(
    #             portal_division_id=portal_division_id,
    #             status=ARTICLE_STATUS_IN_PORTAL.published).filter(
    #             or_(
    #                 ArticlePortal.title.ilike("%" + search_text + "%"),
    #                 ArticlePortal.short.ilike("%" + search_text + "%"),
    #                 ArticlePortal.long.ilike("%" + search_text + "%")))
    #
    #     if page_size:
    #         query = query.limit(page_size)
    #     if page:
    #         query = query.offset(page*page_size) if int(page) in range(
    #             0, int(pages)) else query.offset(pages*page_size)
    #
    #     return query

    @staticmethod
    def get_one_article(article_id):
        article = g.db.query(ArticleCompany).filter_by(id=article_id).one()
        return article

    @staticmethod
    def get_articles_submitted_to_company(company_id):
        articles = g.db.query(ArticleCompany).filter_by(company_id=company_id).all()
        return articles if articles else []

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
        self.editor_user_id = editor_user_id
        self.company_id = company_id
        self.name = name
        self.short = short
        self.long = long
        self.article_company_id = article_company_id
        self.article_id = article_id
