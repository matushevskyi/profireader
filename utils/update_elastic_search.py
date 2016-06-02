import sys
sys.path.append('..')
from profapp.models.articles import Article, ArticleCompany, ArticleCompanyHistory, \
    ArticlePortalDivision
from profapp.models.company import Company, UserCompany
from profapp.models.files import File
from profapp.models.users import User
from profapp.models.portal import Portal
from profapp.models.country import Country
from profapp.models.pr_base import MLStripper
from sqlalchemy import create_engine, event
from profapp.models.pr_base import Search
from profapp.constants.SEARCH import RELEVANCE
import re
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
import http.client, urllib.parse

from datetime import datetime
from elasticsearch import Elasticsearch

from profapp import create_app, load_database



# if __name__ == '__main__':


# classes = [ArticlePortalDivision, Article, ArticleCompany, ArticleCompanyHistory,
#            Company, UserCompany, File, User, Portal]

classes = [ArticlePortalDivision]

engine = create_engine(ProductionDevelopmentConfig.SQLALCHEMY_DATABASE_URI)
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))


def add_to_search(target=None):

    if hasattr(target, 'search_fields'):
        target_fields = ','.join(target.search_fields.keys())
        target_dict = target.get_client_side_dict(fields=target_fields + ',id')
        options = {'relevance': lambda field_name: getattr(RELEVANCE, field_name),
                   'processing': lambda text: MLStripper().strip_tags(text),
                   'index': lambda target_id: target_id}
        md_time = datetime.datetime.now()
        default_time = datetime.datetime.now()
        if hasattr(target, 'publishing_tm'):
            md_time = getattr(target, 'publishing_tm', default_time)
        elif hasattr(target, 'md_tm'):
            md_time = getattr(target, 'md_tm', default_time)
        elif hasattr(target, 'cr_tm'):
            md_time = getattr(target, 'cr_tm', default_time)
        elif hasattr(target, 'registered_tm'):
            md_time = getattr(target, 'registered_tm', default_time)
        for field in target_fields.split(','):
            field_options = target.search_fields[field]
            field_options.update({key: options[key] for key in options
                                 if key not in field_options.keys()})
            pos = getattr(target, 'position', 0)
            position = pos if pos else 0
            db_session.add(Search(index=field_options['index'](target_dict['id']),
                                  table_name=target.__tablename__,
                                  relevance=field_options['relevance'](field), kind=field,
                                  text=field_options['processing'](str(target_dict[field])),
                                  position=position, md_tm=md_time))

def update_search_table(target=None):

    if hasattr(target, 'search_fields'):
        if delete_from_search(target):
            add_to_search(target)
        else:
            add_to_search(target)


def delete_from_search(target):
    if hasattr(target, 'search_fields') and \
            db_session.query(Search).filter_by(index=target.id).count():
        db_session.query(Search).filter_by(index=target.id).delete()
        return True
    return False


if __name__ == '__main__':
    # time = datetime.datetime.now()
    elem_count = 0
    quantity = 0
    percent_to_str = ''
    percents = []
    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

    # app_run()
    # answer = input(
    #     "Are you sure? \n If you'l start this process, your database will be overwritten. "
    #     "Yes|No")
    # prompt = True if answer in ['yes', 'Yes', 'y', 'YES', 'tak'] else False
    # if not prompt:
    #     exit('The script has been closed.')
    # for cls in classes:
    #     if hasattr(cls, 'search_fields'):
    #         elem_count += db_session.query(cls).count()
    #         quantity = elem_count
        es = Elasticsearch(hosts='elastic.profi')



        for cls in classes:
            for id in [o[0] for o in db_session.query(cls.id).filter_by(search_reindexed = 0).all()]:
                # print(id)
                object = db_session.query(cls).filter_by(id=id).one()
                object.search_reindexed = 1
                object.omit_validation = True

                es.index(index='profireader', doc_type='article', id=id, body=object.get_elastic_search_data())

                # conn = http.client.HTTPSConnection("elastic.profi", 9200)
                #
                # params = urllib.parse.urlencode({'@number': 12524, '@type': 'issue', '@action': 'show'})
                # headers = {"Content-type": "application/x-www-form-urlencoded",
                #                 "Accept": "text/plain"}
                # conn = http.client.HTTPConnection("profireader.com")
                # conn.request("POST", "", params, headers)
                # response = conn.getresponse()
                # print(response.status, response.reason)
                # data = response.read()
                # # data
                # conn.close()
                print(id)
        # execute_time = datetime.datetime.now()-time
        db_session.commit()
        print('Updated successfully')
    # print('Execution time: {time}'.format(time=execute_time))
    # db_session.commit()


