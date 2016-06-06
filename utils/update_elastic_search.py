import sys

sys.path.append('..')
from profapp.models.articles import Article, ArticleCompany, ArticleCompanyHistory, \
    ArticlePortalDivision

from sqlalchemy import create_engine, event
from profapp.models.pr_base import Search
from profapp.constants.SEARCH import RELEVANCE
import re
from sqlalchemy.orm import scoped_session, sessionmaker
from config import ProductionDevelopmentConfig
import datetime
import http.client, urllib.parse
from profapp.models.elastic import PRElastic

from datetime import datetime

from profapp import create_app, load_database
import argparse

# if __name__ == '__main__':


# classes = [ArticlePortalDivision, Article, ArticleCompany, ArticleCompanyHistory,
#            Company, UserCompany, File, User, Portal]

classes = [ArticlePortalDivision]



def add_documents():
    indexes = PRElastic.get_structure()
    for ei in indexes:
        ei.insert_all_documents()
    # for doctype, doc_properties in es.get_elastic_fields().items():
    #     id_field = doc_properties['id']
    #     main_class = list(id_field['depend_on'].keys())[0]
    #     for o in db_session.query(main_class).all():
    #         elastic_doc = {}
    #         for f_name, f_prop in doc_properties.items():
    #             elastic_doc[f_name] = f_prop['depend_on'][main_class][1](o)
    #
    #         es.add(doctype, doctype, o.id, elastic_doc)
    # db_session.commit()


def create_indexes():
    # mappings = {}
    settings = {
        # "index": {
        #     "number_of_shards": 3,
        #     "number_of_replicas": 2
        # }
    }
    indexes = PRElastic.get_structure()

    for ei in indexes:
        ei.delete()
        ei.create()


if __name__ == '__main__':
    # time = datetime.datetime.now()

    parser = argparse.ArgumentParser(description='profireader application type')
    parser.add_argument("whattodo", default='reindex')
    args = parser.parse_args()

    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

        if args.whattodo == 'create_elastic_indexes':
            create_indexes()

        elif args.whattodo == 'reindex_elastic_documents':
            add_documents()

