from blinker import signal
from ...models import db, Meta, PostMeta
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Table, Pagination
import os.path

show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
edit_article = signal('edit_article')


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
                                 url_for('.show_template', id=template.id))
                     , Hyperlink('Hyperlink', template.post_metas.count(),
                                 url_for('.list_articles', template=template.key))))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '模板',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
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


@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['all_template_metas'] = Meta.templates()
    contents.append(os.path.join('template', 'templates', 'content_template.html'))
    scripts.append(os.path.join('template', 'templates', 'script_template.html'))
    widgets.append(os.path.join('template', 'templates', 'widget_content_template.html'))
