from ...models import db
from .models import Tag
from ..post.models import Post
from flask import current_app, url_for, flash, render_template
from ...element_models import Hyperlink, Plain, Table, Pagination
from ...utils import slugify
from ..post.signals import post_keywords, custom_list
from ...admin.signals import sidebar, show_list, manage, edit, submit, dispatch
from ..article.signals import article_list_column_head, article_list_column, submit_article, edit_article, article, \
    restore_article, article_list_url
from ...signals import restore
from ...plugins import add_template_file
from pathlib import Path
import os.path
from ..article import signals as article_signals


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@show_list.connect_via('tag')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Tag.query.order_by(Tag.name) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    tags = pagination.items
    head = ('', '名称', '别名', '文章数')
    rows = []
    for tag in tags:
        rows.append((tag.id
                     , Hyperlink('Hyperlink', tag.name,
                                 url_for('.edit', type='tag', id=tag.id))
                     , Plain('Plain', tag.slug)
                     , Hyperlink('Hyperlink', len(tag.posts),
                                 url_for('.show_list', type='post', sub_type='article', tag=tag.slug))))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '标签',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, '.show_list', args)
    }


@custom_list.connect
def custom_list(sender, args, query):
    if 'tag' in args and args['tag'] != '':
        query['query'] = query['query'].join(Post.tags).filter(Tag.slug == args['tag'])
    return query


@article_signals.custom_list.connect
def custom_list(sender, request, query_wrap, **kwargs):
    if 'tag' in request.args and request.args['tag'] != '':
        query_wrap['query'] = query_wrap['query'].join(Post.tags).filter(Tag.slug == request.args['tag'])


@article_signals.list_column_head.connect
@article_list_column_head.connect
def article_list_column_head(sender, head, **kwargs):
    head.append('标签')


@article_list_column.connect
def article_list_column(sender, post, row):
    row.append([Hyperlink('Hyperlink', tag.name,
                          url_for('.show_list', type='post', sub_type='article', tag=tag.slug)) for tag in post.tags])


@article_signals.list_column.connect
def article_list_column(sender, article, row, **kwargs):
    row.append([Hyperlink('Hyperlink', tag.name,
                          url_for('.show_list', type='post', sub_type='article', tag=tag.slug)) for tag in
                article.tags])


@manage.connect_via('tag')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_tag_name = Tag.query.get(ids[0]).name
            for tag in Tag.query.filter(Tag.id.in_(ids)):
                db.session.delete(tag)
            db.session.commit()
            message = '已删除标签"' + first_tag_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个标签'
            flash(message)


@edit_article.connect
def edit_article(sender, context, widgets, scripts, **kwargs):
    context['all_tag_name'] = [tag.name for tag in Tag.query.all()]
    context['tag_names'] = [tag.name for tag in context['post'].tags]
    add_template_file(widgets, Path(__file__), 'templates', 'widget_content_tag.html')
    add_template_file(scripts, Path(__file__), 'templates', 'widget_script_tag.html')


@submit_article.connect
def submit_article(sender, form, post):
    tag_names = form.getlist('tag-name')
    tag_names = set(tag_names)
    tags = []
    for tag_name in tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag is None:
            tag = Tag(name=tag_name, slug=slugify(tag_name))
            db.session.add(tag)
            db.session.flush()
        tags.append(tag)
    post.tags = tags


@edit.connect_via('tag')
def edit(sender, args, context, contents, **kwargs):
    id = args.get('id', type=int)
    tag = None
    if id is not None:
        tag = Tag.query.get(id)
    context['tag'] = tag
    add_template_file(contents, Path(__file__), 'templates', 'content.html')


@submit.connect_via('tag')
def submit(sender, args, form, **kwargs):
    id = form.get('id', type=int)
    if id is None:
        tag = Tag()
    else:
        tag = Tag.query.get(id)
    tag.name = form['name']
    tag.slug = form['slug']
    tag.description = form['description']
    if tag.id is None:
        db.session.add(tag)
    db.session.commit()


@post_keywords.connect
def post_keywords(sender, post, keywords, **kwargs):
    keywords.extend(category.name for category in post.categories)


@article.connect
def article(sender, article_metas, **kwargs):
    add_template_file(article_metas, Path(__file__), 'templates', 'main', 'article_meta.html')


@restore_article.connect
def restore_article(sender, data, article, **kwargs):
    if 'tags' in data:
        ts = []
        for tag in data['tags']:
            t = Tag.query.filter_by(name=tag).first()
            if t is None:
                t = Tag.create(name=tag, slug=slugify(tag))
                db.session.add(t)
                db.session.flush()
            ts.append(t)
        article.tags = ts
        db.session.flush()


@restore.connect
def restore(sender, data, **kwargs):
    if 'tag' in data:
        for tag in data['tag']:
            t = Tag.query.filter_by(name=tag['name']).first()
            if t is None:
                t = Tag.create(name=tag['name'], slug=slugify(tag['name']),
                               description=tag['description'])
                db.session.add(t)
                db.session.flush()
            else:
                t.description = tag['description']


@dispatch.connect_via('tag')
def dispatch(sender, request, templates, **kwargs):
    page = request.args.get('page', 1, type=int)
    pagination = Tag.query.order_by(Tag.name) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    tags = pagination.items
    templates.append(render_template(os.path.join('tag', 'templates', 'list.html'), tags=tags,
                                     signal_article_list_url=article_list_url))
