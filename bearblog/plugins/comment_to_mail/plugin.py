import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

import redis
from flask import current_app, redirect, request
from rq import Queue, Connection, get_failed_queue

from bearblog.plugins import current_plugin, plugin_url_for, plugin_route
from .models import Message
from bearblog.plugins.comment.models import Comment
from bearblog.plugins.comment.plugin import get_comment_show_info
from bearblog.extensions import db
from bearblog.models import Signal
from bearblog.settings import get_setting, set_setting

opener = urllib.request.build_opener()


@Signal.connect('deploy', 'bearblog')
def deploy():
    set_setting('client_id', name='Application ID', value='', value_type='str')
    set_setting('redirect_url', name='Redirect URL', value='', value_type='str')
    set_setting('scope', name='Delegated Permissions', value='', value_type='str')
    set_setting('client_secret', name='Application Secret', value='', value_type='str')
    set_setting('authorize_url', name='Authorize URL', value='', value_type='str')
    set_setting('token_url', name='Token URL', value='', value_type='str')
    set_setting('api_base_url', name='API Base URL', value='', value_type='str')
    set_setting('access_token', value='', value_type='str', visibility='invisible')
    set_setting('expires_at', value='0', value_type='int', visibility='invisible')
    set_setting('refresh_token', value='', value_type='str', visibility='invisible')
    set_setting('token_type', value='', value_type='str', visibility='invisible')


@Signal.connect('admin_sidebar_item', 'plugins')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '设置',
                'url': plugin_url_for('settings', _component='admin')
            },
            {
                'type': 'link',
                'name': '我',
                'url': plugin_url_for('me', _component='admin')
            },
            {
                'type': 'link',
                'name': '管理提醒',
                'url': plugin_url_for('list', _component='admin')
            }
        ]
    }


def is_authorized():
    access_token = get_setting('access_token').value
    if access_token == '':
        return False
    expires_at = get_setting('expires_at').value
    if expires_at - 10 < int(time.time()):
        token_url = get_setting('token_url').value
        refresh_token = get_setting('refresh_token').value
        client_id = get_setting('client_id').value
        redirect_url = get_setting('redirect_url').value
        scope = get_setting('scope').value
        client_secret = get_setting('client_secret').value
        if refresh_token == '':
            return False
        with urllib.request.urlopen(token_url, data=urllib.parse.urlencode({'client_id': client_id, 'grant_type': 'refresh_token', 'scope': scope, 'refresh_token': refresh_token, 'redirect_uri': redirect_url, 'client_secret': client_secret}).encode()) as f:
            result = json.loads(f.read().decode())
            set_setting('access_token', value=result['access_token'])
            set_setting('token_type', value=result['token_type'])
            set_setting('expires_at', value=str(int(time.time()) + result['expires_in']))
            set_setting('refresh_token', value=result['refresh_token'])
    token_type = get_setting('token_type').value
    access_token = get_setting('access_token').value
    opener.addheaders = [('Authorization', token_type + ' ' + access_token)]
    return True


@plugin_route('/settings', 'settings', _component='admin')
def account():
    return Signal.send('get_rendered_settings', 'settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug}, signals=current_plugin.signal.signals)


@plugin_route('/login', 'login', _component='admin')
def login():
    authorize_url = get_setting('authorize_url').value
    client_id = get_setting('client_id').value
    scope = get_setting('scope').value
    redirect_url = get_setting('redirect_url').value

    return redirect(authorize_url + '?' + urllib.parse.urlencode({'client_id': client_id, 'response_type': 'code', 'redirect_uri': redirect_url, 'response_mode': 'query', 'scope': scope}))


@plugin_route('/authorize', 'authorize', _component='admin')
def authorize():
    token_url = get_setting('token_url').value
    client_id = get_setting('client_id').value
    scope = get_setting('scope').value
    redirect_url = get_setting('redirect_url').value
    client_secret = get_setting('client_secret').value

    code = request.args['code']
    with urllib.request.urlopen(token_url, data=urllib.parse.urlencode({'client_id': client_id, 'grant_type': 'authorization_code', 'scope': scope, 'code': code, 'redirect_uri': redirect_url, 'client_secret': client_secret}).encode()) as f:
        result = json.loads(f.read().decode())
        set_setting('access_token', value=result['access_token'])
        set_setting('token_type', value=result['token_type'])
        set_setting('expires_at', value=str(int(time.time()) + result['expires_in']))
        set_setting('refresh_token', value=result['refresh_token'])
        opener.addheaders = [('Authorization', result['token_type'] + ' ' + result['access_token'])]
    return redirect(plugin_url_for('me', _component='admin'))


@plugin_route('/me', 'me', _component='admin')
def me():
    if is_authorized():
        api_base_url = get_setting('api_base_url').value
        try:
            f = opener.open(api_base_url + '/me')
            me = json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            me = None
    else:
        me = None
    return current_plugin.render_template('me.html', me=me, login_url=plugin_url_for('login', _component='admin'))


@Signal.connect('comment_submitted', 'comment')
def comment_submitted(comment):
    message = Message(comment=comment, status='未发送')
    db.session.add(message)
    db.session.commit()

    comment_info = get_comment_show_info(comment)
    if comment.parent == 0:
        recipient = 'zhantong1994@163.com'
        body = current_plugin.render_template('message_to_author.html', comment_info=comment_info, author_name=comment.author.name, author_body=comment.body_html)
    else:
        parent_comment = Comment.query.get(comment.parent).first()
        recipient = parent_comment.author.email
        if recipient is None or recipient == '':
            return
        body = current_plugin.render_template('message_to_recipient.html', comment_info=comment_info, recipient_name=parent_comment.author.name, author_name=comment.author.name, author_body=comment.body_html, recipient_body=parent_comment.body_html)
    subject = '[' + comment_info['title'] + '] ' + '一文有新的评论'

    redis_url = current_app.config['REDIS_URL']
    with Connection(redis.from_url(redis_url)):
        q = Queue()
        job = q.enqueue(send_mail, recipient, subject, body, message.id)
        message.job_id = job.id
        db.session.commit()


def send_mail(recipient, subject, body, message_id):
    message = Message.query.get(message_id)
    api_base_url = get_setting('api_base_url').value
    if not is_authorized():
        return
    token_type = get_setting('token_type').value
    access_token = get_setting('access_token').value
    request = urllib.request.Request(api_base_url + '/me/messages', data=json.dumps({'subject': subject, 'body': {'contentType': 'HTML', 'content': body}, 'toRecipients': [{'emailAddress': {'address': recipient}}]}).encode(), method='POST')
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
    request = urllib.request.Request(api_base_url + '/me/messages/' + message_id + '/send', method='POST')
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


@plugin_route('/list', 'list', _component='admin')
def list_messages():
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
        pagination = Message.query.paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
        messages = pagination.items
        with Connection(redis.from_url(current_app.config['REDIS_URL'])):
            queue = Queue()
        return current_plugin.render_template('list.html', messages=messages, queue=queue, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}})
