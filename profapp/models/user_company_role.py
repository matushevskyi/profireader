from sqlalchemy import Column, ForeignKey, Integer
from db_init import Base, db_session
from ..constants.TABLE_TYPES import TABLE_TYPES
from flask import g
from ..constants.USER_ROLES import ROLES
from ..constants.STATUS import STATUS
from .user_model import User
statuses = STATUS()

class UserCompanyRole(Base):
    __tablename__ = 'user_company_role'
    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)
    role_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company_role.id'), nullable=False)
    status = Column(TABLE_TYPES['status'], nullable=False)

    def __init__(self, user_id=None, company_id=None, role_id=None, status=None):
        self.user_id = user_id
        self.company_id = company_id
        self.role_id = role_id
        self.status = status

    def subscribe_to_company(self, id):

        role = ROLES()
        db_session.add(UserCompanyRole(user_id=g.user.id, company_id=id,
                                       role_id=role.READER(), status=statuses.NONACTIVE()))
        db_session.commit()

    def query_non_active(self, id):

        query = db_session.query(UserCompanyRole).filter_by(status=statuses.NONACTIVE()).\
            filter_by(company_id=id).all()
        non_active_subscribers = []
        for user in query:
            non_active_subscribers.append(db_session.query(User).filter_by(id=user.user_id).first())
        return non_active_subscribers

    def apply_request(self, comp_id, user_id):

        db_session.query(UserCompanyRole).filter_by(status=statuses.NONACTIVE()).\
            filter_by(company_id=comp_id).filter_by(user_id=user_id).update({'status': statuses.ACTIVE()})
        db_session.commit()

class CompanyRole(Base):
    __tablename__ = 'company_role'
    id = Column(TABLE_TYPES['role'], primary_key=True)
