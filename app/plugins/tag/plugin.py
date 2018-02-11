from blinker import signal
from ...models import db
from .models import Tag
from ..post.models import Post
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Table, Pagination
import os.path
from ...utils import slugify
from . import signals

sidebar = signal('sidebar')
show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
article_list_column_head = signal('article_list_column_head')
article_list_column = signal('article_list_column')
edit_article = signal('edit_article')
submit_article = signal('submit_article')
edit = signal('edit')
submit = signal('submit')


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('tag', 'templates', 'sidebar.html'))


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


@article_list_column_head.connect
def article_list_column_head(sender, head):
    head.append('标签')


@article_list_column.connect
def article_list_column(sender, post, row):
    row.append([Hyperlink('Hyperlink', tag.name,
                          url_for('.show_list', type='post', sub_type='article', tag=tag.slug)) for tag in post.tags])


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
    widgets.append(os.path.join('tag', 'templates', 'widget_content_tag.html'))
    scripts.append(os.path.join('tag', 'templates', 'widget_script_tag.html'))


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
    contents.append(os.path.join('tag', 'templates', 'content.html'))


@submit.connect_via('tag')
def submit(sender, form):
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


@signals.post_keywords.connect
def post_keywords(sender, post, keywords, **kwargs):
    keywords.extend(category.name for category in post.categories)
