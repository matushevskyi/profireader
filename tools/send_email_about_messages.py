import sys

sys.path.append('..')

from profapp.utils import email_utils
from profapp.models.users import User
from flask import g, url_for

from sqlalchemy.sql import text, and_

from profapp import create_app, load_database
import argparse
import datetime


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='send greetings message')
    parser.add_argument("--user_id")
    args = parser.parse_args()

    app = create_app(apptype='profi', config='config.CommandLineConfig')

    with app.app_context():
        first_email_in = 3600
        next_emails_in = 24 * 3600

        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()
        have_unread = 'message_unread_count("user".id, NULL)>0 OR notification_unread_count("user".id)>0 OR contact_request_count("user".id)>0'
        not_logged_in_first = 'seconds_ago(last_seen_tm) > %s AND seconds_ago(last_seen_tm) < %s AND seconds_ago(last_informed_about_unread_communication_tm)>seconds_ago(last_seen_tm)' % (first_email_in, next_emails_in)
        not_logged_in_next =  'seconds_ago(last_seen_tm) > %s AND seconds_ago(last_informed_about_unread_communication_tm) > %s' % (first_email_in + next_emails_in, next_emails_in)

        send = text("(%s) AND ((%s) OR (%s))" % (have_unread, not_logged_in_first, not_logged_in_next))


        def compile(q):
            print(q.statement.compile(compile_kwargs={"literal_binds": True}))

        if args.user_id:
            users = g.db.query(User).filter(and_(User.id == args.user_id), send).all()
        else:
            users = g.db.query(User).filter(send).all()

        if len(users):
            print("%s users found" % (len(users),))
            for u in users:
                print('sending email to', u.id, u.full_name, u.address_email)
                try:
                    g.lang = u.lang
                    email_utils.send_email_from_template(
                        fromname='Profireader notifications',
                        send_to_email=[u.address_email], subject='Unread communication exists',
                        template='messenger/email_unread_communication_exists.html',
                        dictionary={'user': u, 'url_messenger': url_for('messenger.messenger')})
                    u.last_informed_about_unread_communication_tm = datetime.datetime.utcnow()
                    u.save()
                    g.db.commit()
                except Exception as e:
                    print(e)
        else:
            print("no users found")

