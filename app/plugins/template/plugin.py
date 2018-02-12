from blinker import signal
from ...models import db
from ..post.models import Post
from .models import Template, TemplateField
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Table, Pagination
from jinja2 import Template as Jinja2Tempalte
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
article = signal('article')
page = signal('page')


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('template', 'templates', 'sidebar.html'))


@show_list.connect_via('template')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Template.query.order_by(Template.name) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    templates = pagination.items
    head = ('', '名称', '文章数')
    rows = []
    for template in templates:
        rows.append((template.id
                     , Hyperlink('Hyperlink', template.name,
                                 url_for('.edit', type='template', id=template.id))
                     , Hyperlink('Hyperlink', len(template.posts),
                                 url_for('.show_list', type='post', sub_type='article', template=template.slug))))
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
        query['query'] = query['query'].join(Post.template).filter(Template.slug == args['template'])
    return query


@manage.connect_via('tag')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_template_name = Template.query.get(ids[0]).name
            for template in Template.query.filter(Template.id.in_(ids)):
                db.session.delete(template)
            db.session.commit()
            message = '已删除模板"' + first_template_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个模板'
            flash(message)


@edit_page.connect
@edit_article.connect
def edit_article(sender, context, contents, widgets, scripts, **kwargs):
    context['all_template'] = Template.query.all()
    contents.append(os.path.join('template', 'templates', 'content_template.html'))
    scripts.append(os.path.join('template', 'templates', 'script_template.html'))
    widgets.append(os.path.join('template', 'templates', 'widget_content_template.html'))


@submit_page.connect
@submit_article.connect
def submit_article(sender, form, post):
    field_keys = form.getlist('template-field-key')
    field_values = form.getlist('template-field-value')
    post.template_fields = []
    for key, value in zip(field_keys, field_values):
        template_field = TemplateField(post=post, key=key, value=value)
        db.session.add(template_field)
        db.session.flush()
        post.template_fields.append(template_field)


@submit_page_with_action.connect_via('enable-template')
@submit_article_with_action.connect_via('enable-template')
def submit_article_with_action_enable_template(sender, form, post):
    template_id = form['template-id']
    post.template = Template.query.get(int(template_id))
    db.session.commit()


@submit_page_with_action.connect_via('disable-template')
@submit_article_with_action.connect_via('disable-template')
def submit_article_with_action_enable_template(sender, form, post):
    post.template = None
    db.session.commit()


@edit.connect_via('template')
def edit(sender, args, context, contents, **kwargs):
    id = args.get('id', type=int)
    template = None
    if id is not None:
        template = Template.query.get(id)
    context['template'] = template
    contents.append(os.path.join('template', 'templates', 'content.html'))


@submit.connect_via('template')
def submit(sender, form):
    id = form.get('id', type=int)
    if id is None:
        template = Template()
    else:
        template = Template.query.get(id)
    template.name = form['name']
    template.slug = form['slug']
    template.description = form['description']
    template.body = form['body']
    if template.id is None:
        db.session.add(template)
    db.session.commit()


@article.connect
def article(sender, post, context, article_content, **kwargs):
    if post.template is not None:
        template = Jinja2Tempalte(post.template.body)
        article_content['article_content'] = template
        context.update({template_field.key: eval(template_field.value) for template_field in post.template_fields})


@page.connect
def page(sender, post, context, page_content, contents, scripts):
    if post.template is not None:
        template = Jinja2Tempalte(post.template.body)
        page_content['page_content'] = template
        context.update({template_field.key: eval(template_field.value) for template_field in post.template_fields})
