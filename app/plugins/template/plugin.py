from blinker import signal
from ...models import db, Meta, PostMeta, Post
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Table, Pagination
import os.path

sidebar = signal('sidebar')
show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
edit_article = signal('edit_article')
submit_article = signal('submit_article')
submit_article_with_action = signal('submit_article_with_action')
edit_page = signal('edit_page')
submit_page = signal('submit_page')
submit_page_with_action = signal('submit_page_with_action')
edit = signal('edit')
submit = signal('submit')


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('template', 'templates', 'sidebar.html'))


@show_list.connect_via('template')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Meta.query_templates().order_by(Meta.key) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    templates = pagination.items
    head = ('', '名称', '文章数')
    rows = []
    for template in templates:
        rows.append((template.id
                     , Hyperlink('Hyperlink', template.key,
                                 url_for('.edit', type='template', id=template.id))
                     , Hyperlink('Hyperlink', template.post_metas.count(),
                                 url_for('.show_list', type='article', template=template.key))))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '模板',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, '.show_list', args)
    }


@custom_list.connect
def custom_list(sender, args, query):
    if 'template' in args and args['template'] != '':
        query['query'] = query['query'].join(PostMeta, Meta).filter(
            Meta.key == args['template'] and Meta.type == 'template')
    return query


@manage.connect_via('tag')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_template_name = Meta.query.get(ids[0]).key
            for template in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(template)
            db.session.commit()
            message = '已删除模板"' + first_template_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个模板'
            flash(message)


@edit_page.connect
@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['all_template_metas'] = Meta.templates()
    contents.append(os.path.join('template', 'templates', 'content_template.html'))
    scripts.append(os.path.join('template', 'templates', 'script_template.html'))
    widgets.append(os.path.join('template', 'templates', 'widget_content_template.html'))


@submit_page.connect
@submit_article.connect
def submit_article(sender, form, post):
    field_keys = form.getlist('field-key')
    field_values = form.getlist('field-value')
    post.field_metas = []
    for key, value in zip(field_keys, field_values):
        post.field_metas.append(Meta.create_field(key=key, value=value))


@submit_page_with_action.connect_via('enable-template')
@submit_article_with_action.connect_via('enable-template')
def submit_article_with_action_enable_template(sender, form):
    id = form['id']
    template_id = form['template']
    post = Post.query.get(int(id))
    post.template_post_meta = PostMeta(post=post, meta_id=int(template_id))
    db.session.commit()


@submit_page_with_action.connect_via('disable-template')
@submit_article_with_action.connect_via('disable-template')
def submit_article_with_action_enable_template(sender, form):
    id = form['id']
    post = Post.query.get(int(id))
    post.template_post_meta = None
    db.session.commit()


@edit.connect_via('template')
def edit(sender, args, context, styles, hiddens, contents, widgets, scripts):
    id = args.get('id', type=int)
    template = None
    if id is not None:
        template = Meta.query.get(id)
    context['template'] = template
    contents.append(os.path.join('template', 'templates', 'content.html'))


@submit.connect_via('template')
def submit(sender, form):
    id = form.get('id', type=int)
    if id is None:
        template = Meta().create_template()
    else:
        template = Meta.query.get(id)
    template.key = form['key']
    template.value = form['value']
    template.description = form['description']
    if template.id is None:
        db.session.add(template)
    db.session.commit()
