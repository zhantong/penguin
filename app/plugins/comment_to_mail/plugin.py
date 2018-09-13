import os
import smtplib
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import sys
from flask import current_app, url_for
from ..comment.signals import comment_submitted
from .models import CommentToMail, OAuth2Token
from ...models import db
from threading import Thread
from ...admin.signals import sidebar, edit, submit
from ...plugins import add_template_file
from pathlib import Path
from ... import signals as app_signals
from authlib.flask.client import OAuth
from ..models import Plugin

comment_to_mail = Plugin('评论邮件提醒', 'comment_to_mail')
comment_to_mail_instance = comment_to_mail

oauth = OAuth()


@app_signals.init_app.connect
def init_app(sender, app, **kwargs):
    oauth.init_app(app)

    oauth.register('microsoft',
                   client_id='4859a905-c6f4-4b9f-8e65-69f8b02eb26b',
                   client_secret='secret',
                   authorize_url='https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
                   authorize_params={'response_type': 'code',
                                     'response_mode': 'query'},
                   access_token_url='https://login.microsoftonline.com/common/oauth2/v2.0/token',
                   client_kwargs={'scope': 'User.Read'},
                   api_base_url='https://graph.microsoft.com/v1.0/',
                   save_request_token=save_request_token,
                   fetch_request_token=fetch_request_token
                   )


def save_request_token(token):
    print('save')
    print(token)


def fetch_request_token():
    item = OAuth2Token.query.filter_by(
        name='microsoft'
    ).first()
    print('fetch')
    return item.to_token()


@comment_to_mail.route('admin', '/list', '管理')
def article_list(request, templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(oauth.microsoft.authorize_redirect(
        redirect_uri=url_for('main.index', _external=True) + comment_to_mail.url_for('/authorize')[1:]))


@comment_to_mail.route('admin', '/authorize')
def authorize(request, **kwargs):
    # token = oauth.microsoft.authorize_access_token()
    # print(token)
    print(oauth.microsoft.get('me').json())


@comment_to_mail.route('admin', '/me', '我')
def me(request, **kwargs):
    print(oauth.microsoft.get('me').json())


def _format_address(s):
    name, address = parseaddr(s)
    return formataddr((Header(name, 'utf-8').encode(), address))


def send_email(app, to_address, subject, content):
    from_address = app.config['MAIL_USERNAME']
    password = app.config['MAIL_PASSWORD']

    msg = MIMEText(content, 'plain', 'utf-8')
    msg['From'] = _format_address('Penguin <%s>' % from_address)
    msg['To'] = _format_address('%s <%s>' % (to_address, to_address))
    msg['Subject'] = Header(subject, 'utf-8').encode()

    log_file = tempfile.TemporaryFile()
    available_fd = log_file.fileno()
    log_file.close()
    os.dup2(2, available_fd)
    log_file = tempfile.TemporaryFile()
    os.dup2(log_file.fileno(), 2)

    try:
        smtp = smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        smtplib.stderr = log_file
        smtp.set_debuglevel(2)
        smtp.login(from_address, password)
        smtp.sendmail(from_address, [to_address], msg.as_string())
        smtp.quit()
    except smtplib.SMTPException as e:
        is_success = False
    else:
        is_success = True

    sys.stderr.flush()
    log_file.flush()
    log_file.seek(0)
    stderr_bytes = log_file.read()
    log_file.close()
    os.dup2(available_fd, 2)
    os.close(available_fd)

    return is_success, stderr_bytes.decode()


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@edit.connect_via('comment_to_mail')
def edit(sender, contents, **kwargs):
    add_template_file(contents, Path(__file__), 'templates', 'content.html')


@submit.connect_via('comment_to_mail')
def submit(sender, args, form, **kwargs):
    app = current_app._get_current_object()
    is_sent, log = send_email(app, form['address'], form['subject'], form['content'])
    print(log)


@comment_submitted.connect
def comment_submitted(sender, comment, **kwargs):
    if comment.author.email:
        app = current_app._get_current_object()

        def async_function(app):
            with app.app_context():
                is_sent, log = send_email(app, comment.author.email, '新的评论', comment.body)
                comment_to_mail = CommentToMail(is_sent=is_sent, log=log, comment=comment)
                db.session.add(comment_to_mail)
                db.session.commit()

        thread = Thread(target=async_function, args=[app])
        thread.start()
