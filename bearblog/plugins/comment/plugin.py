import json
import urllib.parse
import urllib.request
from datetime import datetime

from flask import flash, request, jsonify, session
from flask_login import current_user
from sqlalchemy import desc

from bearblog.plugins import current_plugin
from .js_captcha import confuse_string
from bearblog.plugins.comment.models import Comment
from bearblog.plugins.models import Plugin
from bearblog.models import Signal, User, Role
from bearblog.extensions import db
from bearblog.utils import format_comments
from bearblog import component_route

ENABLE_TENCENT_CAPTCHA = True


@component_route('/comment', 'submit_comment', 'main', methods=['POST'])
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
    if 'article_id' in meta:
        article = Signal.send('article', 'get_article', article_id=meta['article_id'])
        article.comments.append(comment)
        db.session.commit()
    elif 'page_id' in meta:
        page = Signal.send('page', 'get_page', page_id=meta['page_id'])
        page.comments.append(comment)
        db.session.commit()
    current_plugin.signal.send_this('on_new_comment', comment=comment, meta=meta)
    current_plugin.signal.send_this('comment_submitted', comment=comment)
    return jsonify({
        'code': 0,
        'message': '发表成功'
    })


def get_comment_show_info(comment):
    if comment.article is not None:
        return {
            'title': comment.article.title,
            'url': Signal.send('article', 'article_url', article=comment.article, anchor='comment-' + str(comment.id))
        }
    if comment.page is not None:
        return {
            'title': comment.page.title,
            'url': Signal.send('page', 'page_url', page=comment.page, anchor='comment-' + str(comment.id))
        }


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
        pagination = Comment.query.order_by(desc(Comment.timestamp)).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        comments = pagination.items
        templates.append(current_plugin.render_template('list.html', comment_instance=current_plugin, comments=comments, get_comment_show_info=get_comment_show_info, pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {}, 'url_for': current_plugin.url_for}))
        scripts.append(current_plugin.render_template('list.js.html', meta=meta))


def show_widget(session, comments, meta):
    js_str, true_str = confuse_string()
    session['js_captcha'] = true_str
    return {
        'slug': 'comment',
        'html': current_plugin.render_template('comment.html', comments=comments, ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA),
        'script': current_plugin.render_template('comment.js.html', meta=meta, ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA, js_captcha_str=js_str)
    }


@Signal.connect('article', 'show_article_widget')
def show_article_widget(session, article):
    meta = {
        'article_id': article.id
    }
    comments = format_comments(article.comments)
    return show_widget(session, comments, meta)


@Signal.connect('page', 'show_page_widget')
def show_page_widget(session, page):
    meta = {
        'page_id': page.id
    }
    comments = format_comments(page.comments)
    return show_widget(session, comments, meta)


def restore(comments):
    restored_comments = []

    def process_comments(comments, parent=0):
        for comment in comments:
            if type(comment['author']) is str:
                author = User.query.filter_by(name=comment['author']).one()
            else:
                author = User.create(role=Role.guest(), name=comment['author']['name'], email=comment['author']['email'], member_since=datetime.utcfromtimestamp(comment['author']['member_since']))
                db.session.add(author)
                db.session.flush()
            c = Comment.create(body=comment['body'], timestamp=datetime.utcfromtimestamp(comment['timestamp']), ip=comment['ip'], agent=comment['agent'], parent=parent, author=author)
            db.session.add(c)
            db.session.flush()
            restored_comments.append(c)
            process_comments(comment['children'], parent=c.id)

    process_comments(comments)
    return restored_comments


@Signal.connect('article', 'restore')
def article_restore(article, data):
    if 'comments' in data:
        article.comments = restore(data['comments'])


@Signal.connect('page', 'restore')
def page_restore(page, data):
    if 'comments' in data:
        page.comments = restore(data['comments'])


@Signal.connect('main', 'widget')
def main_widget():
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    return {
        'slug': 'latest_comments',
        'name': '最近回复',
        'html': current_plugin.render_template('widget_latest_comments', 'widget.html', comments=comments, get_comment_show_info=get_comment_show_info),
        'is_html_as_list': True
    }


@current_plugin.signal.connect_this('get_rendered_num_comments')
def get_rendered_tag_items(comments):
    return current_plugin.render_template('num_comments.html', comments=comments)


@Signal.connect('article', 'duplicate')
def article_duplicate(old_article, new_article):
    new_article.comments = old_article.comments


@Signal.connect('page', 'duplicate')
def article_duplicate(old_page, new_page):
    new_page.comments = old_page.comments


def _article_meta(article):
    return current_plugin.render_template('num_comments.html', comments=article.comments)


@Signal.connect('article', 'meta')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article', 'article_list_item_meta')
def article_list_item_meta(article):
    return _article_meta(article)


@Signal.connect('page', 'meta')
def article_meta(page):
    return current_plugin.render_template('num_comments.html', comments=page.comments)


@Signal.connect('article', 'custom_contents_column')
def article_custom_contents_column():
    def content_func(article):
        return current_plugin.render_template('article_contents_item.html', comments=article.comments)

    return {
        'title': '评论',
        'item': {
            'content': content_func,
        }
    }
