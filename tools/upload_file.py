import sys

sys.path.append('..')
from profapp.models.files import File, FileContent
from flask import g
from profapp import create_app, prepare_connections
import argparse, os

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("--file_id")
    parser.add_argument("--file_name")
    parser.add_argument("--parent_id")
    parser.add_argument("--mime")
    parser.add_argument("--file")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')
    with app.app_context():
        prepare_connections(app)(echo=True)

        f = open(args.file, 'rb')
        file = File(parent_id=args.parent_id,
                    root_folder_id=args.parent_id,
                    name=args.file_name,
                    company_id=None,
                    mime=args.mime,
                    size=os.path.getsize(args.file)
                    ).save()
        file_cont = FileContent(file=file, content=f.read())

        file.save()
        file.id = args.file_id
        g.db.commit()
