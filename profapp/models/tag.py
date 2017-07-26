from ..constants.TABLE_TYPES import TABLE_TYPES
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from .pr_base import PRBase, Base


class Tag(Base, PRBase):
    __tablename__ = 'tag'
    id = Column(TABLE_TYPES['id_profireader'], nullable=False, primary_key=True)

    text = Column(TABLE_TYPES['name'], nullable=False, default='')

    description = Column(TABLE_TYPES['string_500'], nullable=False, default='')

    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal.id', onupdate='CASCADE', ondelete='CASCADE'),
                       primary_key=True, nullable=False)

    portal = relationship('Portal', uselist=False)

    def __init__(self, text='', description='', portal=None):
        self.text = text
        self.description = description
        self.portal = portal

    def get_client_side_dict(self, fields='id|text|description', more_fields=None):
        return self.to_dict(fields, more_fields)


class TagPortalDivision(Base, PRBase):
    __tablename__ = 'tag_portal_division'

    portal_division_id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)

    tag_id = Column(TABLE_TYPES['id_profireader'],
                    ForeignKey(Tag.id, onupdate='CASCADE', ondelete='CASCADE'),
                    primary_key=True, nullable=False)

    portal_id = Column(TABLE_TYPES['id_profireader'], nullable=False)

    ForeignKeyConstraint((portal_division_id, portal_id), ('portal_division.id', 'portal_division.portal_id'))


class TagPublication(Base, PRBase):
    __tablename__ = 'tag_publication'

    publication_id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)

    tag_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Tag.id), primary_key=True, nullable=False)

    portal_division_id = Column(TABLE_TYPES['id_profireader'], nullable=False)

    ForeignKeyConstraint((publication_id, portal_division_id), ('publication.id',
                                                                'publication.portal_division_id'))

    position = Column(TABLE_TYPES['position'], nullable=True, default=1)


class TagMembership(Base, PRBase):
    __tablename__ = 'tag_membership'

    member_company_portal_id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)

    tag_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Tag.id), primary_key=True, nullable=False)

    portal_id = Column(TABLE_TYPES['id_profireader'], nullable=False)

    portal_division_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('portal_division.id'), nullable=False)

    ForeignKeyConstraint((member_company_portal_id, portal_id), ('member_company_portal.id',
                                                                 'member_company_portal.portal_id'))

    # portal = relationship('Portal', uselist=False)
    # portal_division = relationship('PortalDivision', uselist=False)



    # ForeignKeyConstraint((portal_id, tag_id),
    #                      ('tag.portal_id', 'tag.id'),
    #                      onupdate='CASCADE', ondelete='CASCADE')
    #
    # ForeignKeyConstraint((portal_division_id, tag_id),
    #                      ('tag_portal_division.portal_division_id', 'tag_portal_division.tag_id'),
    #                      onupdate='CASCADE', ondelete='CASCADE')
    #
    # ForeignKeyConstraint((member_company_portal_id, portal_id), ('member_company_portal.id',
    #                                                              'member_company_portal.portal_id'),
    #                      onupdate='CASCADE', ondelete='CASCADE')

    position = Column(TABLE_TYPES['position'], nullable=True, default=1)

