from sqlalchemy import Column, Integer, ForeignKey, String, Binary, UniqueConstraint
import re
from ..constants.TABLE_TYPES import TABLE_TYPES
from utils.db_utils import db
from sqlalchemy.orm import relationship, backref
from flask import url_for, g
from .pr_base import PRBase, Base


class File(Base, PRBase):
    __tablename__ = 'file'
    id = Column(TABLE_TYPES['id_profireader'], primary_key=True)
    parent_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))
    root_folder_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'))
    name = Column(TABLE_TYPES['name'], default='', nullable=False)
    mime = Column(String(30), default='text/plain', nullable=False)
    description = Column(TABLE_TYPES['text'], default='', nullable=False)
    copyright = Column(TABLE_TYPES['text'], default='', nullable=False)
    company_id = Column(TABLE_TYPES['id_profireader'],
                        ForeignKey('company.id'),
                        nullable=False)
    article_portal_id = Column(TABLE_TYPES['id_profireader'], ForeignKey('article_portal.id'))
    copyright_author_name = Column(TABLE_TYPES['name'],
                                   default='',
                                   nullable=False)
    ac_count = Column(Integer, default=0, nullable=False)
    size = Column(Integer, default=0, nullable=False)
    author_user_id = Column(TABLE_TYPES['id_profireader'],
                            ForeignKey('user.id'),
                            nullable=False)
    cr_tm = Column(TABLE_TYPES['timestamp'], nullable=False)
    md_tm = Column(TABLE_TYPES['timestamp'], nullable=False)
    ac_tm = Column(TABLE_TYPES['timestamp'], nullable=False)

    UniqueConstraint('name', 'parent_id', name='unique_name_in_folder')

    owner = relationship('User',
                         backref=backref('files', lazy='dynamic'),
                         foreign_keys='File.author_user_id')

    def __init__(self, parent_id=None, name=None, mime='text/plain', size=0,
                 user_id=None, cr_tm=None, md_tm=None, ac_tm=None,
                 root_folder_id=None,
                 company_id=None, author_user_id=None):

        self.parent_id = parent_id
        self.name = name
        self.mime = mime
        self.size = size
        self.user_id = user_id
        self.cr_tm = cr_tm
        self.md_tm = md_tm
        self.root_folder_id = root_folder_id
        self.ac_tm = ac_tm
        self.author_user_id = author_user_id
        self.company_id = company_id

    def __repr__(self):
        return "<File(name='%s', mime=%s', id='%s', parent_id='%s')>" % (
            self.name, self.mime, self.id, self.parent_id)

    @staticmethod
    def is_directory(file_id):
        return db(File, id=file_id)[0].mime == 'directory'

    @staticmethod
    def is_cropable(file):
        return File.is_graphics(file)

    @staticmethod
    def is_graphics(file):
        return re.match('^image/.*', file.mime)

    @staticmethod
    def ancestors(folder_id=None):
        ret = []
        nextf = g.db.query(File).get(folder_id)
        while nextf and len(ret) < 50:
            ret.append(nextf.id)
            nextf = g.db.query(File).get(nextf.parent_id) if nextf.parent_id else None
        return ret[::-1]


    @staticmethod
    def list(parent_id=None, file_manager_called_for = ''):

        default_actions = {}
        # default_actions['choose'] = lambda file: None
        default_actions['download'] = lambda file: None if ((file.mime == 'directory') or (file.mime == 'root')) else True

        actions = {act: default_actions[act] for act in default_actions}

        show = lambda file: True

        if file_manager_called_for == 'file_browse_image':
            actions['choose'] = lambda file: False if None == re.search('^image/.*', file.mime) else True


            # 'cropable': True if File.is_cropable(file) else False,
        ret = list({'size': file.size, 'name': file.name, 'id': file.id, 'parent_id': file.parent_id,
                                'type': 'dir' if ((file.mime == 'directory') or (file.mime == 'root')) else 'file',
                                'date': str(file.md_tm).split('.')[0],
                    'url': file.url(),
                    'actions': {action:actions[action](file) for action in actions}
                    }
                                        for file in db(File, parent_id = parent_id) if show(file))# we need all records from the table "file"

        return ret

    @staticmethod
    def createdir(parent_id=None, name=None, author_user_id=None,
                  root_folder_id = None,
                  company_id=None, copyright='', author=''):
        f = File(parent_id=parent_id, author_user_id=author_user_id,
                 root_folder_id = root_folder_id,
                 name=name, size=0, company_id=company_id, mime='directory')
        # f = File(parent_id=parent_id, author_user_id=author_user_id, 
        #          name=name, size=0, company_id=company_id, copyright=copyright, mime='directory')
        g.db.add(f)
        g.db.commit()
        return f.id

    @staticmethod
    def create_company_dir(company=None, name=None):
        f = File(parent_id=None, author_user_id=company.author_user_id,
                 name=name, size=0, company_id=company.id, mime='directory')
        g.db.add(f)
        company.company_folder.append(f)
        g.db.commit()
        for x in company.company_folder:
            return x.id

    def upload(self, content):
        file_cont = FileContent(file=self, content=content)
        g.db.add(self, file_cont)
        g.db.commit()
        return self

    def url(self):
        server = re.sub(r'^[^-]*-[^-]*-4([^-]*)-.*$', r'\1', self.id)
        return 'http://file' + server + '.profi.ntaxa.com/' + self.id + '/'

    def copy_file(self, company_id = None, parent_folder_id = None, article_portal_id = None, root_folder_id = None):
        file_content = FileContent.get(self.id).detach()
        attr = {}
        if company_id:
            attr['company_id'] = company_id
        if parent_folder_id:
            attr['parent_folder_id'] = parent_folder_id
        if article_portal_id:
            attr['article_portal_id'] = article_portal_id
        if root_folder_id:
            attr['root_folder_id'] = root_folder_id
        new_file = self.detach().attr(attr)
        new_file.save()
        file_content.id = new_file.id
        new_file.file_content = [file_content]
        return new_file


class FileContent(Base, PRBase):
    __tablename__ = 'file_content'
    id = Column(TABLE_TYPES['id_profireader'], ForeignKey('file.id'),
                primary_key=True)
    content = Column(Binary, nullable=False)
    file = relationship('File',
                                uselist=False,
                                backref='file_content')

    def __init__(self, file=None, content=None):
        self.file = file
        self.content = content

        # file.save(os.path.join(root, filename))
        # for tmp_file in os.listdir(root):
        #     st = os.stat(root+'/'+filename)
        #     file_db.name = filename
        #     file_db.md_tm = time.ctime(os.path.getmtime(root+'/'+filename))
        #     file_db.ac_tm = time.ctime(os.path.getctime(root+'/'+filename))
        #     file_db.cr_tm = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        #     file_db.size = st[ST_SIZE]
        #     if os.path.isfile(root+'/'+tmp_file):
        #         file_db.mime = 'file'
        #     els# e:
        #         file_db.mime = 'dir'

        #
        # binary_out.close# ()
        # if os.path.isfile(root+'/'+filename):
        #     os.remove(root+'/'+filename)
        # else:
        #     os.removedirs(root+'/'+filename)
        # g.db.add(file_db)
        # try:
        #     g.db.commit()
        # except PermissionError:
        #     result = {"result":  {
        #             "success": False,
        #             "error": "Access denied to remove file"}
        #          }
        #     g.db.rollback()
        #
        # return result
        # return True
