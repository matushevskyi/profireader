import sys
sys.path.append('..')
from profapp.models.materials import Publication
from profapp.models.portal import MemberCompanyPortal
from profapp.models.elastic import elasticsearch

from profapp import create_app, load_database
import argparse

def recreate_documents():
    for aclass in [Publication, MemberCompanyPortal]:
        aclass.elastic_reindex_all()



def delete_indexes():
    elasticsearch.show_all_indexes()
    elasticsearch.remove_all_indexes()
    elasticsearch.show_all_indexes()


if __name__ == '__main__':
    # time = datetime.datetime.now()

    parser = argparse.ArgumentParser(description='reindex elastic search documents')
    parser.add_argument("whattodo", choices=['delete_elastic_indexes', 'recreate_all_elastic_documents'])
    args = parser.parse_args()

    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

        if args.whattodo == 'delete_elastic_indexes':
            delete_indexes()

        elif args.whattodo == 'recreate_all_elastic_documents':
            recreate_documents()

