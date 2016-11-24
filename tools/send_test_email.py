import sys

sys.path.append('..')

from profapp import create_app, load_database
from profapp.utils import email_utils
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='send test email')
    parser.add_argument("email")
    args = parser.parse_args()

    app = create_app(apptype='profi')
    with app.app_context():
        load_database(app.config['SQLALCHEMY_DATABASE_URI'])()
        email_utils.send_email(subject='test', html='Go to <a href="http://ntaxa.com/">ntaxa</a>!<br/>Bye!',
                               send_to=[args.email])
