from ...models import db, User, Role
from ..comment.models import Comment
from flask import current_app, flash, request, jsonify, render_template, session
from ...main import main
from flask_login import current_user
from sqlalchemy import desc
from ...utils import format_comments
from datetime import datetime
from ..models import Plugin
import json
import urllib.request
import urllib.parse
from .js_captcha import confuse_string

current_plugin = Plugin.current_plugin()

current_plugin.signal.declare_signal('get_widget_latest_comments', return_type='single')
current_plugin.signal.declare_signal('restore', return_type='single')
current_plugin.signal.declare_signal('get_comment_show_info', return_type='single_not_none')
current_plugin.signal.declare_signal('get_widget_rendered_comments', return_type='single')

ENABLE_TENCENT_CAPTCHA = True


@main.route('/comment', methods=['POST'])
def submit_comment():
    js_captcha = request.form.get('js_captcha', type=str)
    print(js_captcha)
    print(session['js_captcha'])
    if js_captcha != session['js_captcha']:
        return jsonify({
            'code': 1,
            'message': '发表失败'
        })
    if request.headers.getlist('X-Forwarded-For'):
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip = request.remote_addr
    if ENABLE_TENCENT_CAPTCHA:
        tencent_captcha = json.loads(request.form.get('tencent_captcha', type=str))
        params = {
            'aid': '2006905249',
            'AppSecretKey': '0L5LG6K3Qe09PGS3P6-6YMQ**',
            'Ticket': tencent_captcha['ticket'],
            'Randstr': tencent_captcha['randstr'],
            'UserIP': ip
        }
        with urllib.request.urlopen(
                'https://ssl.captcha.qq.com/ticket/verify' + '?' + urllib.parse.urlencode(params)) as f:
            result = json.loads(f.read().decode())
            if result['response'] != '1':
                return jsonify({
                    'code': 1,
                    'message': '发表失败'
                })
    meta = json.loads(request.form.get('meta', type=str))
    parent = request.form.get('parent', type=int)
    name = request.form.get('name', type=str)
    email = request.form.get('email', None, type=str)
    body = request.form.get('body', type=str)
    if current_user.is_authenticated:
        author = current_user._get_current_object()
    else:
        author = User.create(role=Role.guest(), name=name, email=email)
        db.session.add(author)
        db.session.flush()
    agent = request.user_agent.string
    comment = Comment(body=body, parent=parent, author=author, ip=ip, agent=agent)
    db.session.add(comment)
    db.session.commit()
    current_plugin.signal.send_this('on_new_comment', comment=comment, meta=meta)
    current_plugin.signal.send_this('comment_submitted', comment=comment)
    return jsonify({
        'code': 0,
        'message': '发表成功'
    })


def get_comment_show_info(comment):
    return current_plugin.signal.send_this('get_comment_show_info', comment=comment,
                                           anchor='comment-' + str(comment.id))


def delete(comment_id):
    comment = Comment.query.get(comment_id)
    comment_name = comment.body
    db.session.delete(comment)
    db.session.commit()
    message = '已删除评论"' + comment_name + '"'
    flash(message)
    return {
        'result': 'OK'
    }


@current_plugin.route('admin', '/list', '管理评论')
def list_tags(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Comment.query.order_by(desc(Comment.timestamp)) \
            .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        comments = pagination.items
        templates.append(
            render_template(current_plugin.template_path('list.html'), comment_instance=current_plugin,
                            comments=comments,
                            get_comment_show_info=get_comment_show_info,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': current_plugin.url_for}))
        scripts.append(render_template(current_plugin.template_path('list.js.html'), meta=meta))


@current_plugin.signal.connect_this('get_widget_rendered_comments')
def get_rendered_comments(sender, session, comments, meta, **kwargs):
    comments = format_comments(comments)
    js_str, true_str = confuse_string()
    session['js_captcha'] = true_str
    return {
        'html': render_template(current_plugin.template_path('comment.html'), comments=comments, meta=meta,
                                ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA),
        'script': render_template(current_plugin.template_path('comment.js.html'), meta=meta,
                                  ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA, js_captcha_str=js_str)
    }


@current_plugin.signal.connect_this('restore')
def restore(sender, comments, **kwargs):
    restored_comments = []

    def process_comments(comments, parent=0):
        for comment in comments:
            if type(comment['author']) is str:
                author = User.query.filter_by(name=comment['author']).one()
            else:
                author = User.create(role=Role.guest(), name=comment['author']['name'],
                                     email=comment['author']['email'],
                                     member_since=datetime.utcfromtimestamp(comment['author']['member_since']))
                db.session.add(author)
                db.session.flush()
            c = Comment.create(body=comment['body'], timestamp=datetime.utcfromtimestamp(comment['timestamp']),
                               ip=comment['ip'], agent=comment['agent'], parent=parent, author=author)
            db.session.add(c)
            db.session.flush()
            restored_comments.append(c)
            process_comments(comment['children'], parent=c.id)

    process_comments(comments)
    return restored_comments


@current_plugin.signal.connect_this('get_widget_latest_comments')
def get_widget_latest_comments(sender, **kwargs):
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    return {
        'slug': 'latest_comments',
        'name': '最近回复',
        'html': render_template(current_plugin.template_path('widget_latest_comments', 'widget.html'),
                                comments=comments, get_comment_show_info=get_comment_show_info)
    }
