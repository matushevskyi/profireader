from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base


class TagPortal(Base, PRBase):
    __tablename__ = 'tag_portal'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)

    tag = Column(TABLE_TYPES['name'], nullable=False, default='')

    description = Column(TABLE_TYPES['string_500'], nullable=False, default='')

    portal_id = Column(TABLE_TYPES['id_profireader'],
                       ForeignKey('portal.id', onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False)

    def __init__(self, tag='', description='', portal_id=None):
        super(TagPortal, self).__init__()
        self.tag = tag
        self.description = description
        self.portal_id = portal_id

    def get_client_side_dict(self, fields='id|tag|description', more_fields=None):
        return self.to_dict(fields, more_fields)


class TagPortalDivision(Base, PRBase):
    __tablename__ = 'tag_portal_division'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)

    portal_division_id = Column(TABLE_TYPES['id_profireader'],
                                ForeignKey('portal_division.id', onupdate='CASCADE', ondelete='CASCADE'),
                                nullable=False)

    tag_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('tag_portal.id'),nullable=False)

    tag_portal_portal_id = Column(TABLE_TYPES['id_profireader'], nullable=False)

    ForeignKeyConstraint((tag_portal_id, tag_portal_portal_id), (TagPortal.id, TagPortal.portal_id),
                         onupdate='CASCADE', ondelete='CASCADE')

    portal_division = relationship('PortalDivision', uselist=False)
    tag_portal = relationship(TagPortal, uselist=False,
                              primaryjoin = tag_portal_id == TagPortal.id,
                              foreign_keys=[TagPortal.id])

    def __init__(self, portal_division=None, tag_portal=None):
        super(TagPortalDivision, self).__init__()
        self.tag_portal = tag_portal
        self.portal_division = portal_division


class TagPortalDivisionArticle(Base, PRBase):
    __tablename__ = 'tag_portal_division_article'

    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)

    article_portal_division_id = Column(TABLE_TYPES['id_profireader'],
                                        ForeignKey('article_portal_division.id', onupdate='CASCADE', ondelete='CASCADE'),
                                        nullable=False)

    tag_portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('tag_portal_division.id'), nullable=False)
    tag_portal_division_portal_division_id = Column(TABLE_TYPES['id_profireader'], nullable=False)
    position = Column(TABLE_TYPES['position'], nullable=True, default=1)

    # ForeignKeyConstraint((tag_portal_division_id, tag_portal_division_portal_division_id),
    #                      (TagPortalDivision.id, TagPortalDivision.portal_division_id),
    #                      onupdate='CASCADE', ondelete='CASCADE')

    article_portal_division = relationship('ArticlePortalDivision', uselist=False)
    tag_portal_division = relationship(TagPortalDivision, uselist=False)

    def __init__(self, article_portal_division=None, tag_portal_division=None):
        # super(TagPortalDivision, self).__init__()
        # self.position = position
        self.article_portal_division = article_portal_division
        self.tag_portal_division = tag_portal_division
