import os
import smtplib
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import sys
from flask import current_app, url_for, redirect, render_template
from ..comment.signals import comment_submitted
from .models import CommentToMail, OAuth2Token
from ...models import db
from threading import Thread
from ...admin.signals import sidebar, edit, submit
from ...plugins import add_template_file
from pathlib import Path
from ... import signals as app_signals
from ..models import Plugin
import urllib.request
import time
import urllib.parse
import json
import urllib.error

comment_to_mail = Plugin('评论邮件提醒', 'comment_to_mail')
comment_to_mail_instance = comment_to_mail

opener = urllib.request.build_opener()


def authorized_required(func):
    def decorated_view(*args, **kwargs):
        token = OAuth2Token.query.filter_by(name='microsoft').first()
        if token is None or token.expires_at - 10 < int(time.time()):
            kwargs['meta']['override_render'] = True
            kwargs['templates'].append(redirect(comment_to_mail.url_for('/login')))
            return
        else:
            opener.addheaders = [('Authorization', token.token_type + ' ' + token.access_token)]
        return func(*args, **kwargs)

    return decorated_view


@comment_to_mail.route('admin', '/login', None)
def login(meta, templates, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(
        'https://login.microsoftonline.com/common/oauth2/v2.0/authorize' + '?' + urllib.parse.urlencode(
            {'client_id': '4859a905-c6f4-4b9f-8e65-69f8b02eb26b', 'response_type': 'code',
             'redirect_uri': url_for('main.index', _external=True) + comment_to_mail.url_for('/authorize')[
                                                                     1:], 'response_mode': 'query',
             'scope': 'User.Read'})))


@comment_to_mail.route('admin', '/authorize')
def authorize(request, meta, templates, **kwargs):
    code = request.args['code']
    with urllib.request.urlopen('https://login.microsoftonline.com/common/oauth2/v2.0/token',
                                data=urllib.parse.urlencode({'client_id': '4859a905-c6f4-4b9f-8e65-69f8b02eb26b',
                                                             'grant_type': 'authorization_code', 'scope': 'User.Read',
                                                             'code': code, 'redirect_uri': url_for('main.index',
                                                                                                   _external=True) + comment_to_mail.url_for(
                                        '/authorize')[1:],
                                                             'client_secret': 'llhHLBNK2(_inmnZV1561]}'}).encode()) as f:
        result = json.loads(f.read().decode())
        token = OAuth2Token.query.filter_by(name='microsoft').first()
        if token is None:
            token = OAuth2Token(name='microsoft')
            db.session.add(token)
            db.session.flush()
        token.token_type = result['token_type']
        token.access_token = result['access_token']
        token.expires_at = int(time.time()) + result['expires_in']
        db.session.commit()
        opener.addheaders = [('Authorization', token.token_type + ' ' + token.access_token)]
    meta['override_render'] = True
    templates.append(redirect(comment_to_mail.url_for('/me')))


@comment_to_mail.route('admin', '/me', '我')
def me(templates, **kwargs):
    try:
        f = opener.open('https://graph.microsoft.com/v1.0/me')
        me = json.loads(f.read().decode())
    except urllib.error.HTTPError as e:
        me = None
    templates.append(render_template(os.path.join('comment_to_mail', 'templates', 'me.html'), me=me,
                                     login_url=comment_to_mail.url_for('/login')))


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
