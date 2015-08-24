from sqlalchemy import Table, Column, Integer, Text, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship, backref

from db_init import Base
from ..constants.TABLE_TYPES import TABLE_TYPES
from ..constants.STATUS import STATUS
from db_init import db_session

from ..controllers.errors import BadDataProvided

from flask import g

def _Q(cls):
    return db_session.query(cls)

def _A():
    return db_session.query(Article)

def _V():
    return db_session.query(ArticleVersion)






class ArticleVersion(Base):

    __tablename__ = 'article_version'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)

    author_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))
    created_from_version_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article_version.id'))
    article_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article.id'))

    name =  Column(TABLE_TYPES['name'], nullable=False)
    short =  Column(TABLE_TYPES['text'], nullable=False)
    long =  Column(TABLE_TYPES['text'], nullable=False)

    article = relationship('Article')

    def __init__(self, created_from_version_id, author_user_id=None, company_id=None, name='', short='', long=''):

        self.author_user_id = author_user_id if author_user_id is not None else g.user_dict['id']

        self.name = name
        self.short = short
        self.long = long
        self.article = Article() if created_from_version_id is None else _A().filter(Article.id == Article.get_one_version(created_from_version_id).article_id).one()

    def save(self):
        db_session.add(self)
        db_session.commit()
        return self


    def create(self):
        pass


class Article(Base):

    __tablename__ = 'article'
    versions = relationship('ArticleVersion', primaryjoin="Article.id==ArticleVersion.article_id", order_by='desc(ArticleVersion.id)')
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)

    @staticmethod
    def list(user_id=None, company_id = None, before_id = None):

        ret = _A()

        if user_id is not None:
            ret = ret.filter(Article.versions.any(author_user_id=user_id))
        if company_id is not None:
            ret = ret.filter(Article.versions.any(company_id=company_id))

        return ret.all()

    @staticmethod
    def get_versions(article_id, author_user_id = None):
        ret = _V().filter_by(article_id=article_id)
        return (ret if author_user_id is None else ret.filter_by(author_user_id=author_user_id)).all()


    @staticmethod
    def get_one_version(article_version_id=None):
        return _V().filter(ArticleVersion.id == article_version_id).one()


