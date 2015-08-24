from sqlalchemy import Column, ForeignKey, Integer
from db_init import Base
from db_init import db_session
from ..constants.TABLE_TYPES import TABLE_TYPES
from flask import g
from ..constants.USER_ROLES import RIGHTS, COMPANY_OWNER
from ..constants.STATUS import STATUS
from .users import User
from ..controllers.errors import StatusNonActivate
from sqlalchemy.orm import relationship, backref

statuses = STATUS()
r = RIGHTS()

def db(*args, **kwargs):
    return db_session.query(args[0]).filter_by(**kwargs)

class UserCompanyRole(Base):
    __tablename__ = 'user_company_role'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_rights = relationship('User', backref=backref('roles'))
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)
    status = Column(TABLE_TYPES['status'], nullable=False)
    right_id = Column(TABLE_TYPES['rights'], ForeignKey('company_right.id'))
    # user_relation = relationship('User', backref=backref('user_role_relation'))

    def __init__(self, user_id=None, company_id=None, status=None, right_id=None, user_rights=None):
        self.user_id = user_id
        self.company_id = company_id
        self.status = status
        self.right_id = right_id
        self.user_rights = user_rights

    @staticmethod
    def subscribe_to_company(id):

        if not db(UserCompanyRole, user_id=g.user_dict['id'], company_id=id).first():
            db_session.add(UserCompanyRole(user_id=g.user_dict['id'], company_id=id,
                                           status=statuses.NONACTIVE()))
            db_session.commit()
        else:
            raise StatusNonActivate

    @staticmethod
    def check_member(id):

        non_active_subscribers = []
        query = db(UserCompanyRole, status=statuses.NONACTIVE(), company_id=id).all()
        for user in query:
            non_active_subscribers.append(db(User, id=user.user_id).first())
        return non_active_subscribers

    @staticmethod
    def apply_request(comp_id, user_id, bool):

        if bool == 'True':
            stat = statuses.ACTIVE()

        else:
            stat = statuses.REJECT()
        db(UserCompanyRole, status=statuses.NONACTIVE(), company_id=comp_id, user_id=user_id).\
            update({'status': stat, 'right_id': 'comment', 'user_rights': db(User, id=user_id)})
        db_session.commit()

class Right(Base):
    __tablename__ = 'company_right'

    id = Column(TABLE_TYPES['rights'], primary_key=True)
    # user_role = relationship('UserCompanyRole', backref=backref('rights_show'))

    def __init__(self, id=None):
        self.id = id

    @staticmethod
    def query_roles(user_id, comp_id):

        query = db(UserCompanyRole, user_id=user_id, company_id=comp_id)
        return query

    @staticmethod
    def add_rights(user_id, comp_id, right):

        user_right = UserCompanyRole(user_id=user_id, company_id=comp_id, status=statuses.ACTIVE(), right_id=right).\
            first()

        # right = Right
        # right.user_role.append(db(UserCompanyRole, user_id=user_id).first())
        db_session.add(user_right)
        db_session.commit()
        user = User()
        user.user_rights.append(user_right)
        return user_right

    @staticmethod
    def show_rights(comp_id):

        rights = {}
        for x in db(UserCompanyRole, company_id=comp_id).all():
            if x.user_id not in rights:
                user = db(User, id=x.user_id).first()
                rights[x.user_id] = {'name': user.user_name, 'rights': [], 'companies': []}
            rights[x.user_id]['rights'].append(x.right_id)
            rights[x.user_id]['companies'] = [comp.id for comp in db(UserCompanyRole, user_id=x.user_id,
                                                                     status=statuses.ACTIVE()).all()]

        # rights = [dict(t) for t in set([tuple(d.items()) for d in rights])]
        return rights

    # def show_users(self, ):

    # def update_rights(self, *args, **kwargs):
    #     new_rights = db(Right, id=self.query_roles(user_id=args[0], comp_id=args[1]).first().right_id.
    #                     update(dict(**kwargs)))
    #     db_session.commit()
    #     return new_rights.rights_show.rights

    # @staticmethod
    # def show_all_rights(comp_id, show_users=False):
    #     company = db(UserCompanyRole, company_id=comp_id).all()
    #     if show_users:
    #         users = [db(User, id=user.user_id) for user in company]
    #         return users
    #     rights = [user.rights_show.id for user in company]

    # def update_rights(self, user_id, comp_id, comment=r.COMMENT(), publish='None', unpublish='None',
    #                   write_articles=r.WRITE_ARTICLES(), moderate_comments='None', manage_content='None',
    #                   manage_members='None', manage_access='None', transfer_ownership='None'):
    #     new_rights = db(Right, id=self.query_roles(user_id=user_id, comp_id=comp_id).first().right_id).update(
    #         {'rights': '{comment},{publish},{unpublish},'
    #                         '{write_articles},{moderate_comments},{manage_content},'
    #                         '{manage_members},{manage_access},'
    #                         '{transfer_ownership}'.format(
    #         comment=comment, publish=publish, unpublish=unpublish, write_articles=write_articles,
    #         moderate_comments=moderate_comments, manage_content=manage_content, manage_members=manage_members,
    #         manage_access=manage_access, transfer_ownership=transfer_ownership)})
    #
        # insert.query_roles(user_id, comp_id).update({insert.rights: '{comment},{publish},{unpublish},{write_articles},'
        #                                                             '{moderate_comments},{manage_content},'
        #                                                             '{manage_members},{manage_access},'
        #                                                             '{transfer_ownership}'.format(
        #     comment=comment, publish=publish, unpublish=unpublish, write_articles=write_articles,
        #     moderate_comments=moderate_comments, manage_content=manage_content, manage_members=manage_members,
        #     manage_access=manage_access, transfer_ownership=transfer_ownership)})
        # insert.user_role.append(db_session.query(UserCompanyRole).filter_by(user_id=g.user_dict['id']).first())
        # print(insert.user_role)
        # print(db_session.query(UserCompanyRole).filter_by(user_id=user.id]).first().rights_show.rights)
        # db_session.commit()
        # return new_rights
