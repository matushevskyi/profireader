from sqlalchemy import Column, Integer, ForeignKey, String, Binary, Float, TIMESTAMP, UniqueConstraint
from db_init import Base, db_session
import re
from ..constants.TABLE_TYPES import TABLE_TYPES
from utils.db_utils import db
from sqlalchemy.orm import relationship

class File(Base):
    __tablename__ = 'file'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    parent_id = Column(String(36), ForeignKey('file.id'))
    name = Column(TABLE_TYPES['name'], default='', nullable=False)
    mime = Column(String(30), default='text/plain', nullable=False)
    description = Column(TABLE_TYPES['text'], default='', nullable=False)
    copyright = Column(TABLE_TYPES['text'], default='', nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('company.id'), nullable=False)
    author_name = Column(TABLE_TYPES['name'], default='', nullable=False)
    ac_count = Column(Integer, default=0, nullable=False)
    size = Column(Integer, default=0, nullable=False)
    author_user_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('user.id'), nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'], nullable=False)
    md_tm = Column(TABLE_TYPES['timestamp'], nullable=False)
    ac_tm = Column(TABLE_TYPES['timestamp'], nullable=False)

    UniqueConstraint('name', 'parent_id', name='inique_name_in_folder')

    def __init__(self, parent_id=None, name=None, mime='text/plain', size=None, user_id=None, cr_tm=None, md_tm=None, ac_tm=None, company_id=None, author_user_id=None, copyright='', author=''):
        self.parent_id = parent_id
        self.name = name
        self.mime = mime
        self.size = size
        self.user_id = user_id
        self.cr_tm = cr_tm
        self.md_tm = md_tm
        self.ac_tm = ac_tm
        self.author_user_id = author_user_id
        self.company_id = company_id

    def __repr__(self):
        return "<File(name='%s', mime=%s', id='%s', parent_id='%s')>" % (
                                self.name, self.mime, self.id, self.parent_id)

    def is_directory(file_id):
        return db(File, id=file_id)[0].mime == 'directory'

    def is_cropable(file):
        return File.is_graphics(file)

    def is_graphics(file):
        return re.match('^image/.*', file.mime)

    def list(parent_id=None):
        return list({'size': file.size, 'name': file.name, 'id': file.id,
                                'cropable': True if File.is_cropable(file) else False,
                                'type': 'dir' if file.mime == 'directory' else 'file',
                                'date': str(file.md_tm).split('.')[0]}
                                        for file in db(File, File.parent_id == parent_id))

    @staticmethod
    def createdir(parent_id=None, name=None, author_user_id=None, company_id=None, copyright='', author=''):
        f = File(parent_id=parent_id, author_user_id=author_user_id, name=name, size=0, company_id=company_id, copyright=copyright, author=author, mime='directory')
        db_session.add(f)
        db_session.commit()
        return f.id

    @staticmethod
    def create_company_dir(company=None, name=None):
        f = File(parent_id=None, author_user_id=company.author_user_id, name=name, size=0,
                 company_id=company.id, mime='directory')
        db_session.add(f)
        company.company_folder.append(f)
        db_session.commit()
        for x in company.company_folder:
            return x.id

    @staticmethod
    def upload(parent_id=None, file=None, company_id=None, author_user_id=None, copyright='', author=''):
        f = File(parent_id=parent_id, author_user_id=author_user_id, name=file.filename, size=0,
                 company_id=company_id, copyright=copyright, author=author, mime=file.content_type)
        db_session.add(f)
        db_session.commit()
        FileContent(file_content=f, content=file.stream.read(-1))
        db_session.commit()
        return f.id


class FileContent(Base):

    __tablename__ = 'file_content'
    id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'), primary_key=True)
    content = Column(Binary, nullable=False)
    file_content = relationship('File', backref='file_information')

    def __init__(self, file_content=None, content=None, id=None):
        self.content = content
        self.id = id
        self.file_content = file_content

        # file.save(os.path.join(root, filename# ))
        # for tmp_file in os.listdir(root# ):
        #     st = os.stat(root+'/'+filenam# e)
        #     file_db.name = filena# me
        #     file_db.md_tm = time.ctime(os.path.getmtime(root+'/'+filename# ))
        #     file_db.ac_tm = time.ctime(os.path.getctime(root+'/'+filename# ))
        #     file_db.cr_tm = strftime("%Y-%m-%d %H:%M:%S", gmtime(# ))
        #     file_db.size = st[ST_SIZ# E]
        #     if os.path.isfile(root+'/'+tmp_file# ):
        #         file_db.mime = 'fil# e'
        #     els# e:
        #         file_db.mime = 'di# r'

        #
        # binary_out.close# ()
        # if os.path.isfile(root+'/'+filename# ):
        #     os.remove(root+'/'+filenam# e)
        # els# e:
        #     os.removedirs(root+'/'+filenam# e)
        # db_session.add(file_d# b)
        # tr# y:
        #     db_session.commit# ()
        # except PermissionErro# r:
        #     result = {"result":#  {
        #             "success": Fals# e,
        #             "error": "Access denied to remove file# "}
        #        #  }
        #     db_session.rollback#(# )
        #
        # return result
        # return True
