import sys

sys.path.append('..')
from profapp.models.users import User
from profapp.models.messenger import Socket, Notification
from flask import g
from sqlalchemy import and_, or_
from profapp.constants

from profapp import create_app, prepare_connections
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("--user_id")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')
    with app.app_context():

        prepare_connections(app)(echo=True)
        if args.user_id:
            users = [g.db.query(User).filter(User.id == args.user_id).one()]
        else:
            users = g.db.query(User).outerjoin(Notification,
                                               and_(Notification.to_user_id == User.id,
                                                    Notification.notification_type == Notification.NOTIFICATION_TYPES[
                                                        'GREETING'])) \
                .filter(Notification.id == None).all()

        for u in users:
            u.NOTIFY_WELCOME()
        g.db.commit()
