from ...models import db
from ..post.models import PostStatus
from .models import PostVersion
from flask import current_app, url_for, flash
from sqlalchemy import desc
from ...element_models import Hyperlink, Plain, Table, Pagination, Datetime
from ...admin.signals import sidebar, show_list, manage, edit, submit
from ..article.signals import submit_article, article, edit_article
from ...plugins import add_template_file
from pathlib import Path


@edit_article.connect
def edit_article(sender, widgets, **kwargs):
    add_template_file(widgets, Path(__file__), 'templates', 'admin', 'widget_content.html')


@submit_article.connect
def submit_article(sender, form, post, **kwargs):
    if post.post_status == PostStatus.published():
        version = form['post-version-version']
        remark = form['post-version-remark']
        post_version = PostVersion(post=post, body=post.body, body_html=post.body_html, version=version, remark=remark)
        db.session.add(post_version)
        db.session.commit()


@article.connect
def article(sender, args, post, context, article_content, before_contents, **kwargs):
    context['post_versions'] = post.post_versions
    add_template_file(before_contents, Path(__file__), 'templates', 'main', 'content.html')
    if 'post_version' in args:
        context['versioned_post'] = PostVersion.query.get(args.get('post_version', int))
        article_content['article_content'] = Path('post_version', 'templates', 'main',
                                                  'article_content.html').as_posix()


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'admin', 'sidebar.html')


@show_list.connect_via('post-version')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = PostVersion.query.order_by(desc(PostVersion.timestamp)).paginate(page, per_page=current_app.config[
        'PENGUIN_POSTS_PER_PAGE'], error_out=False)
    versioned_posts = pagination.items
    head = ('', '标题', '版本', '备注', '时间')
    rows = []
    for versioned_post in versioned_posts:
        rows.append((versioned_post.id
                     , Hyperlink('Hyperlink', versioned_post.post.title,
                                 url_for('.edit', type='post-version', id=versioned_post.id))
                     , Plain('Plain', versioned_post.version)
                     , Plain('Plain', versioned_post.remark)
                     , Datetime('Datetime', versioned_post.timestamp)))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '历史版本',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, '.show_list', args)
    }


@manage.connect_via('post-version')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_versioned_post_name = PostVersion.query.get(ids[0]).post.title
            for post_version in PostVersion.query.filter(PostVersion.id.in_(ids)):
                db.session.delete(post_version)
            db.session.commit()
            message = '已删除历史版本"' + first_versioned_post_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个历史版本'
            flash(message)


@edit.connect_via('post-version')
def edit(sender, args, context, contents, **kwargs):
    id = args.get('id', type=int)
    post_version = PostVersion.query.get(id)
    context['post_version'] = post_version


@submit.connect_via('post-version')
def submit(sender, args, form, **kwargs):
    id = form.get('id', type=int)
    post_version = PostVersion.query.get(id)
    post_version.body = form['body']
    post_version.version = form['version']
    post_version.remark = form['remark']
    db.session.commit()
