import smtplib
from email.mime.text import MIMEText
from config import Config


# def send_async_email(app, msg):
#     with app.app_context():
#         mail.send(msg)
#
#
# def send_email(to, subject, template, **kwargs):
#     app = current_app._get_current_object()
#     msg = Message(app.config['PROFIREADER_MAIL_SUBJECT_PREFIX'] + ' ' +
#                   subject,
#                   sender=app.config['PROFIREADER_MAIL_SENDER'],
#                   recipients=[to])
#     msg.body = render_template(template + '.txt', **kwargs)
#     msg.html = render_template(template + '.html', **kwargs)
#     thr = Thread(target=send_async_email, args=[app, msg])
#     thr.start()
#     return thr

# username=, password=Config.MAIL_PASSWORD

# def __init__(self, ):
#     self.username = username
#     self.password = password

def send_email(subject='', html='', text=None, send_to=[Config.MAIL_GMAIL]):
    msg = MIMEText(html, 'html')
    msg['Subject'] = subject
    msg['From'] = Config.MAIL_USERNAME
    msg['To'] = ','.join(send_to)
    server = smtplib.SMTP(Config.MAIL_SERVER)
    server.starttls()
    server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
    server.sendmail(Config.MAIL_USERNAME, send_to, msg.as_bytes())
    server.quit()


def send_email_from_template(send_to_email=[Config.MAIL_GMAIL], subject='', template=None, **kwargs):
    from flask import current_app, render_template
    app = current_app._get_current_object()
    return send_email(
        subject=app.config['PROFIREADER_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
        html=render_template(template + '.html', **kwargs),
        text=render_template(template + '.txt', **kwargs),
        send_to=send_to_email)
