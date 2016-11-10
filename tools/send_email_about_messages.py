import sys

sys.path.append('..')

from profapp.utils import email_utils
from profapp.models.users import User
from flask import g, url_for
from sqlalchemy.sql import text, and_

from profapp import create_app, load_database
import argparse

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("--user_id")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')

    with app.app_context():

        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()
        if args.user_id:
            users = [g.db.query(User).filter(and_(User.id == args.user_id), text(
                '(message_unread_count("user".id, NULL)>0 OR notification_unread_count("user".id)>0 OR contact_request_count("user".id)>0)')).one()]
        else:
            users = g.db.query(User).filter(text(
                '(message_unread_count("user".id, NULL)>0 OR notification_unread_count("user".id)>0 OR contact_request_count("user".id)>0)')).all()

        for u in users:
            print('sending email to', u.id, u.full_name, u.address_email)
            g.lang = u.lang
            email_utils.send_email_from_template(
                fromname='Profireader notifications',
                send_to_email=[u.address_email], subject='Unread communication exists',
                template='messenger/email_unread_communication_exists.html',
                dictionary={'user': u, 'url_messenger': url_for('messenger.messenger')})
