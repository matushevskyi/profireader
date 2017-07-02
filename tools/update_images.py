import sys

sys.path.append('..')

from profapp.models.materials import Material, FileImageCrop
from profapp.models.company import Company
from profapp.models.portal import Portal

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
from sqlalchemy.sql import or_, and_
import sys

sys.path.append('..')
from profapp.models.materials import Publication
from profapp.models.portal import MemberCompanyPortal

engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)

from profapp import create_app, prepare_connections
import argparse

db_session_select = scoped_session(sessionmaker(autocommit=False,
                                                autoflush=False,
                                                bind=engine))


def update_article_illustrations():
    materials_without_illustrations = db_session_select.query(Material).filter(
        and_(Material.illustration_file_img_id == None, Material._del_image_file_id != None)).all()
    for m in materials_without_illustrations:
        print(m.title)
        try:
            pass
            db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
            mm = db_session.query(Material).filter_by(id=m.id).one()
            mm.illustration = {
                'selected_by_user': {
                    'crop': None,
                    'type': 'browse',
                    'image_file_id': m._del_image_file_id
                }
            }
            db_session.flush()
            db_session.commit()
        except Exception as e:
            print(e)
    pass

# def update_companies_logo():
#     without_logos = db_session_select.query(Company).filter(
#         and_(Company.logo_file_img_id == None, Company._delme_logo_file_id!= None)).all()
#     for m in without_logos:
#         print(m.name)
#         try:
#             pass
#             db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
#             mm = db_session.query(Company).filter_by(id=m.id).one()
#             mm.logo = {
#                 'selected_by_user': {
#                     'crop': None,
#                     'type': 'browse',
#                     'image_file_id': m._delme_logo_file_id
#                 }
#             }
#             db_session.flush()
#             db_session.commit()
#         except Exception as e:
#             print(e)
#     pass

def update_portals_logo():
    without_logos = db_session_select.query(Portal).filter(
        and_(Portal.logo_file_img_id == None, Portal._delme_logo_file_id!= None)).all()
    for m in without_logos:
        print(m.host)
        try:
            pass
            db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
            mm = db_session.query(Portal).filter_by(id=m.id).one()
            mm.logo = {
                'selected_by_user': {
                    'crop': None,
                    'type': 'browse',
                    'image_file_id': m._delme_logo_file_id
                }
            }
            db_session.flush()
            db_session.commit()
        except Exception as e:
            print(e)
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
parser.add_argument("whattodo", help='articles')
args = parser.parse_args()

app = create_app(apptype='profi')

with app.app_context():
    prepare_connections(app)()
    #update_article_illustrations()
    #update_companies_logo()
    update_portals_logo()
    # update_users_avatar()
