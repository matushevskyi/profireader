import smtplib
from email.mime.text import MIMEText
import sys
import traceback
from config import Config
from functools import wraps
from flask import jsonify, render_template


class SendEmail:
    def __init__(self, username=Config.MAIL_USERNAME, password=Config.MAIL_PASSWORD):
        self.username = username
        self.password = password

    def send_email(self, subject='', html='', send_to=(Config.MAIL_GMAIL, )):

        # if exception:
        #     _, _, tb = sys.exc_info()
        #     traceback.print_tb(tb)
        #     tb_info = traceback.extract_tb(tb)
        #     filename_, line_, func_, text_ = tb_info[-1]
        #     message = 'An error occurred on File "{file}" line {line}\n {assert_message}'.format(
        #         line=line_, assert_message=exception.args, file=filename_)
        #     text = message
        # if template:
        #     text = render_template(template + '.html', **kwargs)
        #     msg = MIMEText(text, 'html')
        # else:
        #     msg = MIMEText(text, 'plain')

        msg = MIMEText(html, 'html')
        msg['Subject'] = subject
        msg['From'] = self.username
        msg['To'] = ','.join(send_to)
        server = smtplib.SMTP(Config.MAIL_SERVER)
        server.starttls()
        server.login(self.username, self.password)
        server.sendmail(self.username, send_to, msg.as_bytes())

        server.quit()


    @staticmethod
    def send_email_decorator(**params):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                params.update(kwargs)
                SendEmail().send_email(**params)
                return func(*args, **kwargs)
            return wrapper
        return decorator


@SendEmail.send_email_decorator(subject='Profireader', text='Text', send_to=('profireader.service@gmail.com', ), template=None)
def email_send(subject=None, text=None, send_to=(), template=None):
    return jsonify(dict(message='Email was successfully sent'))
