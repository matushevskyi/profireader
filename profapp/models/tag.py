from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy import CheckConstraint
from .pr_base import PRBase, Base




class TagPortal(Base, PRBase):
    """ This table contains ONLY portal tags not bound to any division"""
    __tablename__ = 'tag_portal'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)

    tag = Column(TABLE_TYPES['name'], nullable=False, default='')

    portal_id = Column(TABLE_TYPES['id_profireader'],
                       ForeignKey('portal.id', onupdate='CASCADE', ondelete='CASCADE'),
                       nullable=False)

    # UniqueConstraint('tag', 'portal_id', name='uc_tag_id_portal_id')

    def __init__(self, tag='', portal_id=None):
        super(TagPortal, self).__init__()
        self.tag = tag
        self.portal_id = portal_id


# class TagPortalDivision(Base, PRBase):
#     __tablename__ = 'tag_portal_division'
#     id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
#     tag_id = Column(TABLE_TYPES['id_profireader'],
#                     ForeignKey(Tag.id, onupdate='CASCADE', ondelete='CASCADE'),
#                     nullable=False)
#     portal_division_id = Column(TABLE_TYPES['id_profireader'],
#                                 ForeignKey('portal_division.id',
#                                            onupdate='CASCADE',
#                                            ondelete='CASCADE'),
#                                 nullable=False)
#
#     UniqueConstraint('tag_id', 'portal_division_id', name='uc_tag_id_portal_division_id')
#
#     tag = relationship('Tag', back_populates='portal_divisions_assoc')
#     portal_division = relationship('PortalDivision', back_populates='tags_assoc')
#     # articles = relationship('ArticlePortalDivision', secondary='tag_portal_division_article',
#     #                         back_populates='portal_division_tags', lazy='dynamic')
#
#     def __init__(self, tag_id=None, portal_division_id=None):
#         super(TagPortalDivision, self).__init__()
#         self.tag_id = tag_id
#         self.portal_division_id = portal_division_id
#
#     # def validate(self, tag_name):
#     #     ret = {'errors': {}, 'warnings': {}, 'notices': {}}
#     #
#     #     if tag_name == '':
#     #         ret['errors']['name'] = 'empty tag is not allowed'
#     #
#     #     portal_bound_tags_dynamic = db(Portal, id=self.portal_division.portal_id).portal_bound_tags_dynamic
#     #     portal_bound_tag_names = map(lambda obj: getattr(obj, 'name'), portal_bound_tags_dynamic)
#     #     if tag_name in portal_bound_tag_names:
#     #         ret['errors']['name'] = 'this portal tag already exists'
#     #
#     #     return ret

#
# # TODO (AA to AA): create trigger for article_portal_division_id and article_portal_division_id:
# # they should refer the same portal_division_id
# # TODO (AA to AA): add a trigger t: position >= 1
# class TagPortalDivisionArticle(Base, PRBase):
#     __tablename__ = 'tag_portal_division_article'
#     id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)
#     article_portal_division_id = Column(TABLE_TYPES['id_profireader'],
#                                         ForeignKey('article_portal_division.id'),
#                                         nullable=False)
#     tag_portal_division_id = Column(TABLE_TYPES['id_profireader'],
#                                     ForeignKey('tag_portal_division.id'),
#                                     nullable=False)
#     position = Column(TABLE_TYPES['int'],
#                       CheckConstraint('position >= 1', name='cc_position_ge_1'),
#                       nullable=False)
#
#     # article_portal_division = relationship('ArticlePortalDivision', backref=backref('tag_assoc', lazy='dynamic'))
#     article_portal_division_select = relationship('ArticlePortalDivision', back_populates='tag_assoc_select')
#     tag_portal_division = relationship('TagPortalDivision', cascade='save-update, merge')
# #     TODO: many to (many to many)...
#     UniqueConstraint('article_portal_division_id', 'tag_portal_division_id', name='uc_article_tag_id')
#
#     def __init__(self, article_portal_division_id=None, tag_portal_division_id=None, position=None):
#         super(TagPortalDivisionArticle, self).__init__()
#         self.article_portal_division_id = article_portal_division_id
#         self.tag_portal_division_id = tag_portal_division_id
#         self.position = position
#
#
# # class KeyWords(Base, PRBase):
