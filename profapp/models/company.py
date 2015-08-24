from sqlalchemy import Column, String, ForeignKey, update
from sqlalchemy.orm import relationship
from db_init import Base, db_session
from ..constants.TABLE_TYPES import TABLE_TYPES
from flask import g
from config import Config
from ..constants.STATUS import STATUS
from ..constants.USER_ROLES import COMPANY_OWNER
from utils.db_utils import db
from .users import User
from ..controllers.errors import StatusNonActivate
from .files import File

class Company(Base):
    __tablename__ = 'company'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    name = Column(TABLE_TYPES['name'], unique=True)
    logo_file = Column(String(36), ForeignKey('file.id'))
    journalist_folder_file_id = Column(String(36), ForeignKey('file.id'))
    corporate_folder_file_id = Column(String(36), ForeignKey('file.id'))
    portal_consist = Column(TABLE_TYPES['boolean'])
    author_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    country = Column(TABLE_TYPES['name'])
    region = Column(TABLE_TYPES['name'])
    address = Column(TABLE_TYPES['name'])
    phone = Column(TABLE_TYPES['phone'])
    phone2 = Column(TABLE_TYPES['phone'])
    email = Column(TABLE_TYPES['email'])
    short_description = Column(TABLE_TYPES['text'])
    user_company_rs = relationship('UserCompany', backref='company')
    # company_folder = relationship('File')

    def __init__(self, name=None, portal_consist=False, author_user_id=None, logo_file=None, country=None, region=None,
                 address=None, phone=None, phone2=None, email=None, short_description=None, user_company_rs=[]):
        self.name = name
        self.portal_consist = portal_consist
        self.author_user_id = author_user_id
        self.logo_file = logo_file
        self.country = country
        self.region = region
        self.address = address
        self.phone = phone
        self.phone2 = phone2
        self.email = email
        self.short_description = short_description
        self.user_company_rs = user_company_rs

    @staticmethod
    def query_all_companies(user_id):

        status = STATUS()
        companies = []
        query_companies = db(UserCompany, user_id=user_id, status=status.ACTIVE()).all()
        for x in query_companies:
            companies = companies+db(Company, id=x.company_id).all()
        return set(companies)

    @staticmethod
    def query_company(company_id):

        company = db(Company, id=company_id).one()
        return company

    def create_company(self, data, file):

        comp_dict = {'author_user_id': g.user_dict['id']}
        status = STATUS()
        for x, y in zip(data.keys(), data.values()):
            comp_dict[x] = y
        company = Company(**comp_dict)
        db_session.add(company)
        db_session.commit()

        user_rbac = UserCompany(user_id=company.author_user_id,
                                company_id=company.id,
                                status=status.ACTIVE())
        db(Company, id=company.id).update({'logo_file': File.upload(file=file, company_id=company.id,
                                                                    parent_id=company.corporate_folder_file_id,
                                                                    author=g.user_dict['name'],
                                                                    author_user_id=g.user_dict['id'])})
        db_session.add(user_rbac)
        db_session.commit()
        r = Right()
        r.add_rights(company.author_user_id, company.id, COMPANY_OWNER)

    @staticmethod
    def update_comp(company_id, data, file):

        comp = db(Company, id=company_id)
        for x, y in zip(data.keys(), data.values()):
            comp.update({x: y})
        if file.filename:
            comp.update({'logo_file': File.upload(file=file, company_id=company_id,
                                                  parent_id=comp.corporate_folder_file_id,
                                                  author=g.user_dict['name'],
                                                  author_user_id=g.user_dict['id'])})
        db_session.commit()

    @staticmethod
    def query_employee(comp_id):

        employee = db(UserCompany, company_id=comp_id, user_id=g.user_dict['id']).first()
        if employee:
            return employee
        return False

    def query_owner_or_member(self, company_id):

        status = STATUS()
        employee = self.query_employee(company_id)
        if not employee:
            return False
        if employee.status == status.ACTIVE():
            return True

class UserCompanyRight(Base):
    __tablename__ = 'user_company_right'
    id = Column(TABLE_TYPES['bigint'], primary_key=True)
    user_company_id = Column(TABLE_TYPES['bigint'], ForeignKey('user_company.id', onupdate='cascade'))
    company_right_id = Column(TABLE_TYPES['rights'], ForeignKey('company_right.id'))

    def __init__(self, user_company_id=None, company_right_id=None):
        self.user_company_id = user_company_id
        self.company_right_id = company_right_id

    @staticmethod
    def subscribe_to_company(company_id):

        status = STATUS()
        if not db(UserCompany, user_id=g.user_dict['id'], company_id=company_id).first():
            user_rbac = UserCompany(user_id=g.user_dict['id'], company_id=company_id,
                                    status=status.NONACTIVE())
            user_rbac.user = db(User, id=g.user_dict['id']).one()
            db_session.add(user_rbac)
            db_session.commit()

        else:
            raise StatusNonActivate

    @staticmethod
    def apply_request(comp_id, user_id, bool):

        status = STATUS()
        r = Right()
        if bool == 'True':
            stat = status.ACTIVE()
            r.add_rights(user_id, comp_id, Config.BASE_RIGHT_IN_COMPANY)
        else:
            stat = status.REJECT()
        db(UserCompany, company_id=comp_id, user_id=user_id,
           status=status.NONACTIVE()).update({'status': stat})
        db_session.commit()

class UserCompany(Base):

    __tablename__ = 'user_company'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'))
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'))
    status = Column(TABLE_TYPES['id_profireader'])
    right = relationship(UserCompanyRight, backref='user_company')

    def __init__(self, user_id=None, company_id=None, status=None, right=[]):
        self.user_id = user_id
        self.company_id = company_id
        self.status = status
        self.right = right

class Right(Base):
    __tablename__ = 'company_right'

    id = Column(TABLE_TYPES['rights'], primary_key=True)

    @staticmethod
    def add_rights(user_id, comp_id, rights):

        ucr = []
        user = db(User, id=user_id).one()
        for right in rights:
            ucr.append(UserCompanyRight(company_right_id=right))
        user_right = db(UserCompany, user_id=user_id, company_id=comp_id).one()
        user_right.user = user
        user_right.company = db(Company, id=comp_id).one()
        user.companies.append(user_right.company)
        user_right.right = ucr
        db_session.commit()

    @staticmethod
    def remove_rights(user_id, comp_id, rights):

        user_right = db(UserCompany, user_id=user_id, company_id=comp_id).one()
        for right in rights:
            user_right.right.remove(UserCompanyRight(company_right_id=right))
            db_session.commit()

    @staticmethod
    def show_rights(comp_id):

        rights = {}
        for x in db(UserCompany, company_id=comp_id).all():
            if x.user_id not in rights:
                rights[x.user_id] = {'name': x.user.user_name, 'user': x.user, 'rights': [], 'companies': [],
                                     'status': x.status}
            rights[x.user_id]['rights'] = [y.company_right_id for y in x.right]
            rights[x.user_id]['companies'] = [x.user.companies]
        return rights
