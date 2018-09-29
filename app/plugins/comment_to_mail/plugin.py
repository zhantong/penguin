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
from ...extensions import db
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
from .models import OAuth2Meta, Message
from ..comment.plugin import get_comment_show_info
from ..comment.models import Comment
import redis
from rq import Queue, Connection, get_failed_queue
from datetime import datetime

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
            render_template(comment_to_mail_instance.template_path('account.html'), client_id=client_id,
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
    templates.append(render_template(comment_to_mail_instance.template_path('me.html'), me=me,
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
    message = Message(comment=comment, status='未发送')
    db.session.add(message)
    db.session.commit()

    comment_info = get_comment_show_info(comment)
    if comment.parent == 0:
        recipient = 'zhantong1994@163.com'
        body = render_template(comment_to_mail_instance.template_path('message_to_author.html'),
                               comment_info=comment_info, author_name=comment.author.name,
                               author_body=comment.body_html)
    else:
        parent_comment = Comment.get(comment.parent).first()
        recipient = parent_comment.author.email
        if recipient is None or recipient == '':
            return
        body = render_template(comment_to_mail_instance.template_path('message_to_recipient.html'),
                               comment_info=comment_info, recipient_name=parent_comment.author.name,
                               author_name=comment.author.name, author_body=comment.body_html,
                               recipient_body=parent_comment.body_html)
    subject = '[' + comment_info['title'] + '] ' + '一文有新的评论'

    redis_url = current_app.config['REDIS_URL']
    with Connection(redis.from_url(redis_url)):
        q = Queue()
        job = q.enqueue(send_mail, recipient, subject, body, message.id)
        message.job_id = job.id
        db.session.commit()


def send_mail(recipient, subject, body, message_id):
    message = Message.query.get(message_id)
    api_base_url = OAuth2Meta.get('api_base_url')
    if not is_authorized():
        return
    token_type = OAuth2Meta.get('token_type')
    access_token = OAuth2Meta.get('access_token')
    request = urllib.request.Request(api_base_url + 'me/messages', data=json.dumps(
        {'subject': subject, 'body': {'contentType': 'HTML', 'content': body},
         'toRecipients': [{'emailAddress': {'address': recipient}}]}).encode(), method='POST')
    request.add_header('Authorization', token_type + ' ' + access_token)
    request.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(request) as f:
        result = json.loads(f.read().decode())
        message_id = result['id']
        web_link = result['webLink']
        message.message_id = message_id
        message.status = '草稿'
        message.web_link = web_link
        db.session.commit()
    if not is_authorized():
        return
    request = urllib.request.Request(api_base_url + 'me/messages/' + message_id + '/send', method='POST')
    request.add_header('Authorization', token_type + ' ' + access_token)
    request.add_header('Content-Length', '0')
    with urllib.request.urlopen(request) as f:
        code = f.code
        if code == 202:
            message.status = '已发送'
            db.session.commit()
    if not is_authorized():
        return
    request = urllib.request.Request(api_base_url + 'me/messages/' + message_id)
    request.add_header('Authorization', token_type + ' ' + access_token)
    request.add_header('Prefer', 'outlook.body-content-type="html"')
    with urllib.request.urlopen(request) as f:
        result = json.loads(f.read().decode())
        sent_date_time = result['sentDateTime']
        recipient = result['toRecipients'][0]['emailAddress']['address']
        web_link = result['webLink']
        message.sent_date_time = datetime.strptime(sent_date_time, '%Y-%m-%dT%H:%M:%SZ')
        message.recipient = recipient
        message.web_link = web_link
        db.session.commit()


@comment_to_mail.route('admin', '/list', '管理提醒')
def list_messages(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'resend':
            comment_id = request.form['comment_id']
            comment_submitted(sender=None, comment=Comment.query.get(comment_id))
        elif request.form['action'] == 'rerun':
            job_id = request.form['job_id']
            redis_url = current_app.config['REDIS_URL']
            with Connection(redis.from_url(redis_url)):
                fq = get_failed_queue()
                fq.requeue(job_id)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Message.query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'],
                                            error_out=False)
        messages = pagination.items
        with Connection(redis.from_url(current_app.config['REDIS_URL'])):
            queue = Queue()
        templates.append(
            render_template(comment_to_mail_instance.template_path('list.html'), messages=messages,
                            queue=queue,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': comment_to_mail_instance.url_for}))
        scripts.append(render_template(comment_to_mail_instance.template_path('list.js.html')))
