import smtplib
from email.mime.text import MIMEText
from config import Config
from profapp import utils

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

def send_email(FromName=None, subject='', html='', text=None, send_to=[Config.MAIL_GMAIL]):
    msg = MIMEText(html, 'html')
    msg['Subject'] = subject
    msg['From'] = "%s <%s>" % (FromName, Config.MAIL_USERNAME) if FromName else Config.MAIL_USERNAME
    msg['To'] = ','.join(send_to)
    server = smtplib.SMTP(Config.MAIL_SERVER)
    server.starttls()
    server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
    server.sendmail(Config.MAIL_USERNAME, send_to, msg.as_bytes())
    server.quit()


def send_email_from_template(send_to_email, subject=None, template=None, dictionary={},
                             fromname=None,
                             language=None):
    from flask import current_app, render_template, g
    from profapp.models.translate import TranslateTemplate


    language = language if language else 'en'
    # (g.user.lang if g and g.user else 'en')

    app = current_app._get_current_object()
    html = render_template(template, **dictionary)

    subj = TranslateTemplate.translate_and_substitute(template=template, language=language, dictionary=dictionary,
                                                      phrase=subject) if subject else ''

    fromname = TranslateTemplate.translate_and_substitute(template=template, language=language, dictionary=dictionary,
                                                          phrase=fromname) if fromname else None

    return send_email(subject=subj, html=html, text=utils.strip_tags(html), send_to=send_to_email,
                      FromName=fromname)
