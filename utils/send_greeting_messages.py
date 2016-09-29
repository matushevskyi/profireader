import sys


sys.path.append('..')
from profapp.models.users import User
from profapp.models.messenger import Contact, Message
from profapp.constants import RECORD_IDS

from flask import Flask, g, request, current_app, session

from profapp import create_app, load_database
import argparse

if __name__ == '__main__':

    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()

        users = g.db.query(User).filter(User.id != RECORD_IDS.SYSTEM_USERS.profireader()).all()

        for u in users:
            proficontact = g.db.query(Contact).filter_by(user1_id=RECORD_IDS.SYSTEM_USERS.profireader(),
                                                         user2_id=u.id).one()

            greetings = g.db.query(Message).filter_by(message_type=Message.MESSAGE_TYPES['PROFIREADER_NOTIFICATION'],
                                                      message_subtype='WELCOME',
                                                      contact_id=proficontact.id).all()

            if (len(greetings) > 0):
                print('greeting exist')
            else:
                print('greeting don`t exist')
                Message.send_greeting_message(u)
