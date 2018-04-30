from blinker import signal
from ...models import db, User, Role
from ..comment.models import Comment
from ..post.models import Post
from flask import current_app, url_for, flash, request, jsonify
from ...element_models import Hyperlink, Table, Pagination, Plain, Datetime
from ...main import main
from flask_login import current_user
from sqlalchemy import desc
import os.path
from ...utils import format_comments
from . import signals

sidebar = signal('sidebar')
show_list = signal('show_list')
manage = signal('manage')
article = signal('article')
page = signal('page')


@main.route('/comment/<int:id>', methods=['POST'])
def submit_comment(id):
    post = Post.query.get_or_404(id)
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
    comment = Comment.create(body=body, parent=parent, author=author, post=post)
    db.session.add(comment)
    db.session.commit()
    return jsonify({
        'code': 0,
        'message': '发表成功'
    })


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('comment', 'templates', 'sidebar.html'))


@show_list.connect_via('comment')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Comment.query.order_by(desc(Comment.timestamp)) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    comments = pagination.items
    head = ('', '标题', '作者', '时间', '内容')
    rows = []
    for comment in comments:
        rows.append((comment.id
                     , Hyperlink('Hyperlink', comment.post.title,
                                 url_for('main.show_post', slug=comment.post.slug,
                                         _anchor='comment-' + str(comment.id)))
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


@article.connect
def article(sender, post, context, contents, **kwargs):
    comments = Comment.query.filter_by(post=post).order_by(Comment.timestamp.desc()).all()
    context['comments'] = format_comments(comments)
    contents.append(os.path.join('comment', 'templates', 'comment.html'))


@page.connect
def page(sender, post, context, page_content, contents, scripts):
    comments = Comment.query.filter_by(post=post).order_by(Comment.timestamp.desc()).all()
    context['comments'] = format_comments(comments)
    contents.append(os.path.join('comment', 'templates', 'comment.html'))


@signals.index.connect
def index(sender, context, right_widgets, **kwargs):
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    context['comments'] = comments
    right_widgets.append(os.path.join('comment', 'templates', 'main', 'widget_content.html'))
