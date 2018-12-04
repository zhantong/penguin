from flask import current_app, redirect, render_template
from ...extensions import db
from ..models import Plugin
import urllib.request
import time
import urllib.parse
import json
import urllib.error
from .models import Message
from ..comment.plugin import get_comment_show_info
from ..comment.models import Comment
import redis
from rq import Queue, Connection, get_failed_queue
from datetime import datetime

current_plugin = Plugin.current_plugin()

opener = urllib.request.build_opener()


@Plugin.Signal.connect('penguin', 'deploy')
def deploy(sender, **kwargs):
    current_plugin.set_setting('client_id', name='Application ID', value='', value_type='str')
    current_plugin.set_setting('redirect_url', name='Redirect URL', value='', value_type='str')
    current_plugin.set_setting('scope', name='Delegated Permissions', value='', value_type='str')
    current_plugin.set_setting('client_secret', name='Application Secret', value='', value_type='str')
    current_plugin.set_setting('authorize_url', name='Authorize URL', value='', value_type='str')
    current_plugin.set_setting('token_url', name='Token URL', value='', value_type='str')
    current_plugin.set_setting('api_base_url', name='API Base URL', value='', value_type='str')
    current_plugin.set_setting('access_token', value='', value_type='str', visibility='invisible')
    current_plugin.set_setting('expires_at', value='0', value_type='int', visibility='invisible')
    current_plugin.set_setting('refresh_token', value='', value_type='str', visibility='invisible')
    current_plugin.set_setting('token_type', value='', value_type='str', visibility='invisible')


def is_authorized():
    access_token = current_plugin.get_setting_value_this('access_token')
    if access_token == '':
        return False
    expires_at = current_plugin.get_setting_value_this('expires_at')
    if expires_at - 10 < int(time.time()):
        token_url = current_plugin.get_setting_value_this('token_url')
        refresh_token = current_plugin.get_setting_value_this('refresh_token')
        client_id = current_plugin.get_setting_value_this('client_id')
        redirect_url = current_plugin.get_setting_value_this('redirect_url')
        scope = current_plugin.get_setting_value_this('scope')
        client_secret = current_plugin.get_setting_value_this('client_secret')
        if refresh_token == '':
            return False
        with urllib.request.urlopen(token_url,
                                    data=urllib.parse.urlencode({'client_id': client_id,
                                                                 'grant_type': 'refresh_token',
                                                                 'scope': scope,
                                                                 'refresh_token': refresh_token,
                                                                 'redirect_uri': redirect_url,
                                                                 'client_secret': client_secret}).encode()) as f:
            result = json.loads(f.read().decode())
            current_plugin.set_setting('access_token', value=result['access_token'])
            current_plugin.set_setting('token_type', value=result['token_type'])
            current_plugin.set_setting('expires_at', value=str(int(time.time()) + result['expires_in']))
            current_plugin.set_setting('refresh_token', value=result['refresh_token'])
    token_type = current_plugin.get_setting_value_this('token_type')
    access_token = current_plugin.get_setting_value_this('access_token')
    opener.addheaders = [('Authorization', token_type + ' ' + access_token)]
    return True


@current_plugin.route('admin', '/settings', '设置')
def account(request, templates, scripts, **kwargs):
    widget = Plugin.Signal.send('settings', 'get_widget_list', category=current_plugin.slug,
                                meta={'plugin': current_plugin.slug})
    templates.append(widget['html'])
    scripts.append(widget['script'])


@current_plugin.route('admin', '/login', None)
def login(meta, templates, **kwargs):
    authorize_url = current_plugin.get_setting_value_this('authorize_url')
    client_id = current_plugin.get_setting_value_this('client_id')
    scope = current_plugin.get_setting_value_this('scope')
    redirect_url = current_plugin.get_setting_value_this('redirect_url')

    meta['override_render'] = True
    templates.append(redirect(
        authorize_url + '?' + urllib.parse.urlencode(
            {'client_id': client_id, 'response_type': 'code', 'redirect_uri': redirect_url, 'response_mode': 'query',
             'scope': scope})))


@current_plugin.route('admin', '/authorize')
def authorize(request, meta, templates, **kwargs):
    token_url = current_plugin.get_setting_value_this('token_url')
    client_id = current_plugin.get_setting_value_this('client_id')
    scope = current_plugin.get_setting_value_this('scope')
    redirect_url = current_plugin.get_setting_value_this('redirect_url')
    client_secret = current_plugin.get_setting_value_this('client_secret')

    code = request.args['code']
    with urllib.request.urlopen(token_url,
                                data=urllib.parse.urlencode({'client_id': client_id,
                                                             'grant_type': 'authorization_code', 'scope': scope,
                                                             'code': code, 'redirect_uri': redirect_url,
                                                             'client_secret': client_secret}).encode()) as f:
        result = json.loads(f.read().decode())
        current_plugin.set_setting('access_token', value=result['access_token'])
        current_plugin.set_setting('token_type', value=result['token_type'])
        current_plugin.set_setting('expires_at', value=str(int(time.time()) + result['expires_in']))
        current_plugin.set_setting('refresh_token', value=result['refresh_token'])
        opener.addheaders = [('Authorization', result['token_type'] + ' ' + result['access_token'])]
    meta['override_render'] = True
    templates.append(redirect(current_plugin.url_for('/me')))


@current_plugin.route('admin', '/me', '我')
def me(templates, **kwargs):
    if is_authorized():
        api_base_url = current_plugin.get_setting_value_this('api_base_url')
        try:
            f = opener.open(api_base_url + '/me')
            me = json.loads(f.read().decode())
        except urllib.error.HTTPError as e:
            me = None
    else:
        me = None
    templates.append(render_template(current_plugin.template_path('me.html'), me=me,
                                     login_url=current_plugin.url_for('/login')))


@Plugin.Signal.connect('comment', 'comment_submitted')
def comment_submitted(sender, comment, **kwargs):
    message = Message(comment=comment, status='未发送')
    db.session.add(message)
    db.session.commit()

    comment_info = get_comment_show_info(comment)
    if comment.parent == 0:
        recipient = 'zhantong1994@163.com'
        body = render_template(current_plugin.template_path('message_to_author.html'),
                               comment_info=comment_info, author_name=comment.author.name,
                               author_body=comment.body_html)
    else:
        parent_comment = Comment.query.get(comment.parent).first()
        recipient = parent_comment.author.email
        if recipient is None or recipient == '':
            return
        body = render_template(current_plugin.template_path('message_to_recipient.html'),
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
    api_base_url = current_plugin.get_setting_value_this('api_base_url')
    if not is_authorized():
        return
    token_type = current_plugin.get_setting_value_this('token_type')
    access_token = current_plugin.get_setting_value_this('access_token')
    request = urllib.request.Request(api_base_url + '/me/messages', data=json.dumps(
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


@current_plugin.route('admin', '/list', '管理提醒')
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
            render_template(current_plugin.template_path('list.html'), messages=messages,
                            queue=queue,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': current_plugin.url_for}))
        scripts.append(render_template(current_plugin.template_path('list.js.html')))
