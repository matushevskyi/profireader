import sys

sys.path.append('..')
from profapp.models.users import User
from profapp.models.messenger import Contact, Message, Notification
from main_domain import MAIN_DOMAIN
from flask import g

from profapp import create_app, load_database
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("user_id")
    parser.add_argument("some_text")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')
    with app.app_context():

        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()
        if args.user_id:
            users = [g.db.query(User).filter(User.id == args.user_id).one()]
        else:
            users = g.db.query(User).all()

        for u in users:

            if args.user_id:
                print('sending greetings')
                Notification.send_greeting_message(u, args.some_text)
            else:
                pass
                # greetings = g.db.query(Message).filter_by(message_type=Message.MESSAGE_TYPES['PROFIREADER_NOTIFICATION'],
                #                                       message_subtype='WELCOME',
                #                                       contact_id=proficontact.id).all()

                # if (len(greetings) > 0):
                #     print('greeting exist. skipped')
                # else:
                #     print('greeting don`t exist')
                #     Notification.send_greeting_message(u)

        g.db.commit()