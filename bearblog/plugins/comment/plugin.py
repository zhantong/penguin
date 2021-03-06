import json
import urllib.parse
import urllib.request
from datetime import datetime

from flask import flash, request, jsonify, session
from flask_login import current_user
from sqlalchemy import desc

from bearblog.plugins import current_plugin, plugin_route, plugin_url_for
from .js_captcha import confuse_string
from bearblog.plugins.comment.models import Comment
from bearblog.settings import get_setting
from bearblog.models import Signal, User, Role
from bearblog.extensions import db
from bearblog.utils import format_comments
from bearblog import component_route

ENABLE_TENCENT_CAPTCHA = True

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


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
        article = Signal.send('get_article', 'article', article_id=meta['article_id'])
        article.comments.append(comment)
        db.session.commit()
    elif 'page_id' in meta:
        page = Signal.send('get_page', 'page', page_id=meta['page_id'])
        page.comments.append(comment)
        db.session.commit()
    Signal.send('on_new_comment', comment=comment, meta=meta)
    Signal.send('comment_submitted', comment=comment)
    return jsonify({
        'code': 0,
        'message': '发表成功'
    })


@Signal.connect('admin_sidebar_item', 'plugins')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '管理评论',
                'url': plugin_url_for('list', _component='admin')
            }
        ]
    }


def get_comment_show_info(comment):
    if comment.article is not None:
        return {
            'title': comment.article.title,
            'url': Signal.send('article_url', 'article', article=comment.article, anchor='comment-' + str(comment.id))
        }
    if comment.page is not None:
        return {
            'title': comment.page.title,
            'url': Signal.send('page_url', 'page', page=comment.page, anchor='comment-' + str(comment.id))
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


@plugin_route('/list', 'list', _component='admin')
def list_tags():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Comment.query.order_by(desc(Comment.timestamp)).paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
        comments = pagination.items
        return current_plugin.render_template('list.html', comments=comments, get_comment_show_info=get_comment_show_info, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}})


def show_widget(session, comments, meta):
    js_str, true_str = confuse_string()
    session['js_captcha'] = true_str
    return {
        'slug': 'comment',
        'html': current_plugin.render_template('comment.html', comments=comments, ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA),
        'script': current_plugin.render_template('comment.js.html', meta=meta, ENABLE_TENCENT_CAPTCHA=ENABLE_TENCENT_CAPTCHA, js_captcha_str=js_str)
    }


@Signal.connect('api_proxy', 'article')
def api_proxy(widget, path, request, article):
    if widget == 'comment':
        if request.method == 'POST':
            splits = path.split('/')
            if len(splits) == 1:
                comment_id = 0
            else:
                comment_id = int(splits[1])
            data = request.json
            if request.headers.getlist('X-Forwarded-For'):
                ip = request.headers.getlist('X-Forwarded-For')[0]
            else:
                ip = request.remote_addr
            author = User.create(role=Role.guest(), name=data['name'], email=data['email'])
            db.session.add(author)
            db.session.flush()
            agent = request.user_agent.string
            comment = Comment(body=data['content'], parent=comment_id, author=author, ip=ip, agent=agent)
            db.session.add(comment)
            db.session.commit()
            article.comments.append(comment)
            db.session.commit()
            return jsonify({'result': 'OK'})
        else:
            def convert(comments):
                result = []
                for comment in comments:
                    result.append({
                        'comment': comment['comment'].to_json('basic'),
                        'children': convert(comment['children'])
                    })
                return result

            comments = format_comments(article.comments)
            return jsonify({
                'count': len(article.comments),
                'value': convert(comments)
            })


@Signal.connect('show_article_widget', 'article')
def show_article_widget(session, article):
    meta = {
        'article_id': article.id
    }
    comments = format_comments(article.comments)
    return show_widget(session, comments, meta)


@Signal.connect('show_page_widget', 'page')
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


@Signal.connect('restore', 'article')
def article_restore(article, data):
    if 'comments' in data:
        article.comments = restore(data['comments'])


@Signal.connect('restore', 'page')
def page_restore(page, data):
    if 'comments' in data:
        page.comments = restore(data['comments'])


@Signal.connect('widget', 'main')
def main_widget():
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    return {
        'slug': 'latest_comments',
        'name': '最近回复',
        'html': current_plugin.render_template('widget_latest_comments', 'widget.html', comments=comments, get_comment_show_info=get_comment_show_info),
        'is_html_as_list': True
    }


@Signal.connect('get_rendered_num_comments')
def get_rendered_tag_items(comments):
    return current_plugin.render_template('num_comments.html', comments=comments)


@Signal.connect('duplicate', 'article')
def article_duplicate(old_article, new_article):
    new_article.comments = old_article.comments


@Signal.connect('duplicate', 'page')
def article_duplicate(old_page, new_page):
    new_page.comments = old_page.comments


def _article_meta(article):
    return current_plugin.render_template('num_comments.html', comments=article.comments)


@Signal.connect('meta', 'article')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article_list_item_meta', 'article')
def article_list_item_meta(article):
    return {
        'name': '评论数',
        'slug': current_plugin.slug,
        'value': len(article.comments)
    }


@Signal.connect('to_json', 'article')
def article_to_json(article, level):
    return 'comment', len(article.comments)


@Signal.connect('meta', 'page')
def page_meta(page):
    return current_plugin.render_template('num_comments.html', comments=page.comments)


@Signal.connect('custom_contents_column', 'article')
def article_custom_contents_column():
    def content_func(article):
        return current_plugin.render_template('article_contents_item.html', comments=article.comments)

    return {
        'title': '评论',
        'item': {
            'content': content_func,
        }
    }
