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
from flask import g, session, app, current_app
from sqlalchemy.sql import or_, and_
import re
from sqlalchemy import event
from ..constants.SEARCH import RELEVANCE
from datetime import datetime
from .files import FileImg, FileImgDescriptor
from .. import utils
from ..constants.FILES_FOLDERS import FOLDER_AND_FILE
from .elastic import PRElasticField, PRElasticDocument
from config import Config
import simplejson


class Contact(Base, PRBase):
    __tablename__ = 'contact'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True, nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'])
    md_tm = Column(TABLE_TYPES['timestamp'])

    user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))
    contacted_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(User.id))

    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Company.id))
    portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey(Portal.id))


