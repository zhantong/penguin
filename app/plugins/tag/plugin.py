from blinker import signal
from ...models import db
from ..post.models import Meta, PostMeta
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Table, Pagination
import os.path

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
    sidebars.append(os.path.join('category', 'templates', 'sidebar.html'))


@show_list.connect_via('tag')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Meta.query_tags().order_by(Meta.value) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    tags = pagination.items
    head = ('', '名称', '别名', '文章数')
    rows = []
    for tag in tags:
        rows.append((tag.id
                     , Hyperlink('Hyperlink', tag.value,
                                 url_for('.edit', type='tag', id=tag.id))
                     , Plain('Plain', tag.key)
                     , Hyperlink('Hyperlink', tag.post_metas.count(),
                                 url_for('.show_list', type='article', tag=tag.key))))
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
        query['query'] = query['query'].join(PostMeta, Meta).filter(Meta.key == args['tag'] and Meta.type == 'tag')
    return query


@article_list_column_head.connect
def article_list_column_head(sender, head):
    head.append('标签')


@article_list_column.connect
def article_list_column(sender, post, row):
    row.append([Hyperlink('Hyperlink', tag_post_meta.meta.value,
                          url_for('.show_list', type='article', tag=tag_post_meta.meta.key)) for tag_post_meta
                in post.tag_post_metas.all()])


@manage.connect_via('tag')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_tag_name = Meta.query.get(ids[0]).value
            for tag in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(tag)
            db.session.commit()
            message = '已删除标签"' + first_tag_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个标签'
            flash(message)


@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['all_tag_metas'] = Meta.tags()
    context['tags'] = [tag_post_meta.meta.value for tag_post_meta in context['post'].tag_post_metas.all()]
    widgets.append(os.path.join('tag', 'templates', 'widget_content_tag.html'))
    scripts.append(os.path.join('tag', 'templates', 'widget_script_tag.html'))


@submit_article.connect
def submit_article(sender, form, post):
    tag_names = form.getlist('tag')
    tag_post_metas = []
    for tag_name in tag_names:
        tag = Meta.query_tags().filter_by(value=tag_name).first()
        if tag is None:
            tag = Meta.create_tag(key=tag_name, value=tag_name)
            db.session.add(tag)
            db.session.flush()
        tag_post_meta = PostMeta(post=post, meta=tag)
        tag_post_metas.append(tag_post_meta)
    post.tag_post_metas = tag_post_metas


@edit.connect_via('tag')
def edit(sender, args, context, styles, hiddens, contents, widgets, scripts):
    id = args.get('id', type=int)
    tag = None
    if id is not None:
        tag = Meta.query.get(id)
    context['tag'] = tag
    contents.append(os.path.join('tag', 'templates', 'content.html'))


@submit.connect_via('tag')
def submit(sender, form):
    id = form.get('id', type=int)
    if id is None:
        tag = Meta().create_tag()
    else:
        tag = Meta.query.get(id)
    tag.key = form['key']
    tag.value = form['value']
    tag.description = form['description']
    if tag.id is None:
        db.session.add(tag)
    db.session.commit()
