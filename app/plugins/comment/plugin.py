from ...models import db, User, Role
from ..comment.models import Comment
from ..post.models import Post
from flask import current_app, url_for, flash, request, jsonify, render_template
from ...element_models import Hyperlink, Table, Pagination, Plain, Datetime
from ...main import main
from flask_login import current_user
from sqlalchemy import desc
from ...utils import format_comments
from . import signals
from ...main.signals import index
from ...admin.signals import sidebar, show_list, manage
from ..article.signals import article
from ..page.signals import page
from datetime import datetime
from ..article_list.signals import article_list_meta
from ...plugins import add_template_file
from pathlib import Path
from ..models import Plugin
import os.path
from ..article.plugin import article as article_instance
import json

comment = Plugin('评论', 'comment')
comment_instance = comment


@main.route('/comment', methods=['POST'])
def submit_comment():
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
    if request.headers.getlist('X-Forwarded-For'):
        ip = request.headers.getlist('X-Forwarded-For')[0]
    else:
        ip = request.remote_addr
    agent = request.user_agent.string
    comment = Comment(body=body, parent=parent, author=author, ip=ip, agent=agent)
    db.session.add(comment)
    db.session.commit()
    signals.on_new_comment.send(comment=comment, meta=meta)
    signals.comment_submitted.send(comment=comment)
    return jsonify({
        'code': 0,
        'message': '发表成功'
    })


def get_comment_show_info(comment):
    info = {}
    signals.get_comment_show_info.send(comment=comment, anchor='comment-' + str(comment.id), info=info)
    return info


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@show_list.connect_via('comment')
def show_list(sender, args):
    def get_comment_url(comment):
        if comment.post.post_type == 'article':
            return url_for('main.show_article', slug=comment.post.slug, _anchor='comment-' + str(comment.id))
        elif comment.post.post_type == 'page':
            return url_for('main.show_page', slug=comment.post.slug, _anchor='comment-' + str(comment.id))

    page = args.get('page', 1, type=int)
    pagination = Comment.query.order_by(desc(Comment.timestamp)) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    comments = pagination.items
    head = ('', '标题', '作者', '时间', '内容')
    rows = []
    for comment in comments:
        rows.append((comment.id
                     , Hyperlink('Hyperlink', comment.post.title, get_comment_url(comment))
                     , Plain('Plain', comment.author.name)
                     , Datetime('Datetime', comment.timestamp)
                     , Plain('Plain', comment.body_html)))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '评论',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, '.show_list', args)
    }


@manage.connect_via('comment')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_comment_name = Comment.query.get(ids[0]).body
            for comment in Comment.query.filter(Comment.id.in_(ids)):
                db.session.delete(comment)
            db.session.commit()
            message = '已删除分类"' + first_comment_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '条评论'
            flash(message)


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


@comment.route('admin', '/list', '管理评论')
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
            render_template(os.path.join('comment', 'templates', 'list.html'), comment_instance=comment_instance,
                            comments=comments,
                            get_comment_show_info=get_comment_show_info,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': comment_instance.url_for}))
        scripts.append(render_template(os.path.join('comment', 'templates', 'list.js.html'), meta=meta))


@signals.get_rendered_comments.connect
def get_rendered_comments(sender, comments, rendered_comments, scripts, meta, **kwargs):
    comments = format_comments(comments)
    rendered_comments['rendered_comments'] = render_template(os.path.join('comment', 'templates', 'comment.html'),
                                                             comments=comments, meta=meta)
    scripts.append(render_template(os.path.join('comment', 'templates', 'comment.js.html'), meta=meta))


@page.connect
def page(sender, post, context, page_content, contents, scripts):
    comments = Comment.query.filter_by(post=post).order_by(Comment.timestamp.desc()).all()
    context['comments'] = format_comments(comments)
    add_template_file(contents, Path(__file__), 'templates', 'comment.html')


@index.connect
def index(sender, right_widgets, **kwargs):
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    right_widgets.append(
        render_template(os.path.join('comment', 'templates', 'main', 'widget_content.html'), comments=comments,
                        get_comment_show_info=get_comment_show_info))


@signals.restore.connect
def restore(sender, comments, restored_comments, **kwargs):
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
