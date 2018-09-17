import os
import smtplib
import tempfile
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import sys
from flask import current_app, url_for, redirect, render_template
from ..comment.signals import comment_submitted
from .models import CommentToMail
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
from .models import OAuth2Meta

comment_to_mail = Plugin('评论邮件提醒', 'comment_to_mail')
comment_to_mail_instance = comment_to_mail

opener = urllib.request.build_opener()


def is_authorized():
    access_token = OAuth2Meta.get('access_token')
    if access_token is None:
        return False
    expires_at = int(OAuth2Meta.get('expires_at'))
    if expires_at - 10 < int(time.time()):
        token_url = OAuth2Meta.get('token_url')
        refresh_token = OAuth2Meta.get('refresh_token')
        client_id = OAuth2Meta.get('client_id')
        redirect_url = OAuth2Meta.get('redirect_url')
        scope = OAuth2Meta.get('scope')
        client_secret = OAuth2Meta.get('client_secret')
        if refresh_token is None:
            return False
        with urllib.request.urlopen(token_url,
                                    data=urllib.parse.urlencode({'client_id': client_id,
                                                                 'grant_type': 'refresh_token',
                                                                 'scope': scope,
                                                                 'refresh_token': refresh_token,
                                                                 'redirect_uri': redirect_url,
                                                                 'client_secret': client_secret}).encode()) as f:
            result = json.loads(f.read().decode())
            OAuth2Meta.set('access_token', result['access_token'])
            OAuth2Meta.set('token_type', result['token_type'])
            OAuth2Meta.set('expires_at', str(int(time.time()) + result['expires_in']))
            OAuth2Meta.set('refresh_token', result['refresh_token'])
    token_type = OAuth2Meta.get('token_type')
    access_token = OAuth2Meta.get('access_token')
    opener.addheaders = [('Authorization', token_type + ' ' + access_token)]
    return True


@comment_to_mail.route('admin', '/settings', '设置')
def account(request, templates, **kwargs):
    if request.method == 'GET':
        client_id = OAuth2Meta.get('client_id')
        redirect_url = OAuth2Meta.get('redirect_url')
        scope = OAuth2Meta.get('scope')
        client_secret = OAuth2Meta.get('client_secret')
        authorize_url = OAuth2Meta.get('authorize_url')
        token_url = OAuth2Meta.get('token_url')
        api_base_url = OAuth2Meta.get('api_base_url')
        templates.append(
            render_template(os.path.join('comment_to_mail', 'templates', 'account.html'), client_id=client_id,
                            redirect_url=redirect_url, scope=scope, client_secret=client_secret,
                            authorize_url=authorize_url, token_url=token_url, api_base_url=api_base_url))
    elif request.method == 'POST':
        client_id = request.form.get('client-id', type=str)
        redirect_url = request.form.get('redirect-url', type=str)
        scope = request.form.get('scope', type=str)
        client_secret = request.form.get('client-secret', type=str)
        authorize_url = request.form.get('authorize-url', type=str)
        token_url = request.form.get('token-url', type=str)
        api_base_url = request.form.get('api-base-url', type=str)
        OAuth2Meta.set('client_id', client_id)
        OAuth2Meta.set('redirect_url', redirect_url)
        OAuth2Meta.set('scope', scope)
        OAuth2Meta.set('client_secret', client_secret)
        OAuth2Meta.set('authorize_url', authorize_url)
        OAuth2Meta.set('token_url', token_url)
        OAuth2Meta.set('api_base_url', api_base_url)


@comment_to_mail.route('admin', '/login', None)
def login(meta, templates, **kwargs):
    authorize_url = OAuth2Meta.get('authorize_url')
    client_id = OAuth2Meta.get('client_id')
    scope = OAuth2Meta.get('scope')
    redirect_url = OAuth2Meta.get('redirect_url')

    meta['override_render'] = True
    templates.append(redirect(
        authorize_url + '?' + urllib.parse.urlencode(
            {'client_id': client_id, 'response_type': 'code', 'redirect_uri': redirect_url, 'response_mode': 'query',
             'scope': scope})))


@comment_to_mail.route('admin', '/authorize')
def authorize(request, meta, templates, **kwargs):
    token_url = OAuth2Meta.get('token_url')
    client_id = OAuth2Meta.get('client_id')
    scope = OAuth2Meta.get('scope')
    redirect_url = OAuth2Meta.get('redirect_url')
    client_secret = OAuth2Meta.get('client_secret')

    code = request.args['code']
    with urllib.request.urlopen(token_url,
                                data=urllib.parse.urlencode({'client_id': client_id,
                                                             'grant_type': 'authorization_code', 'scope': scope,
                                                             'code': code, 'redirect_uri': redirect_url,
                                                             'client_secret': client_secret}).encode()) as f:
        result = json.loads(f.read().decode())
        OAuth2Meta.set('access_token', result['access_token'])
        OAuth2Meta.set('token_type', result['token_type'])
        OAuth2Meta.set('expires_at', str(int(time.time()) + result['expires_in']))
        OAuth2Meta.set('refresh_token', result['refresh_token'])
        opener.addheaders = [('Authorization', result['token_type'] + ' ' + result['access_token'])]
    meta['override_render'] = True
    templates.append(redirect(comment_to_mail.url_for('/me')))


@comment_to_mail.route('admin', '/me', '我')
def me(templates, **kwargs):
    if is_authorized():
        api_base_url = OAuth2Meta.get('api_base_url')
        try:
            f = opener.open(api_base_url + '/me')
            me = json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            me = None
    else:
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
