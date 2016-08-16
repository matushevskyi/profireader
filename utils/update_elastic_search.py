import sys

sys.path.append('..')
from profapp.models.materials import Publication
from profapp.models.portal import MemberCompanyPortal
from profapp.models.elastic import elasticsearch


from profapp import create_app, load_database
import argparse


classes = [Publication, MemberCompanyPortal]


def recreate_documents():
    for aclass in classes:
        aclass.elastic_reindex_all()



def delete_indexes():
    elasticsearch.show_all_indexes()
    elasticsearch.remove_all_indexes()
    elasticsearch.show_all_indexes()


if __name__ == '__main__':
    # time = datetime.datetime.now()

    parser = argparse.ArgumentParser(description='profireader application type')
    parser.add_argument("whattodo", default='reindex')
    args = parser.parse_args()

    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

        if args.whattodo == 'delete_elastic_indexes':
            delete_indexes()

        elif args.whattodo == 'recreate_all_elastic_documents':
            recreate_documents()

