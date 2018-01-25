from blinker import signal
from ...models import db, Meta, PostMeta
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Table, Pagination, Select, Option
import os.path
from sqlalchemy.orm import load_only

show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
article_search_select = signal('article_search_select')
edit_article = signal('edit_article')


@show_list.connect_via('category')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Meta.query_categories().order_by(Meta.value) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    categories = pagination.items
    head = ('', '名称', '别名', '文章数')
    rows = []
    for category in categories:
        rows.append((category.id
                     , Hyperlink('Hyperlink', category.value,
                                 url_for('admin.show_category', id=category.id))
                     , Plain('Plain', category.key)
                     , Hyperlink('Hyperlink', category.post_metas.count(),
                                 url_for('.show_list', type='article', category=category.key))))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '分类',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
    }


@custom_list.connect
def custom_list(sender, args, query):
    if 'category' in args and args['category'] != '':
        query['query'] = query['query'].join(PostMeta, Meta).filter(
            Meta.key == args['category'] and Meta.type == 'category')
    return query


@article_search_select.connect
def article_search_select(sender):
    select = Select('Select', 'category', [Option('Option', '全部分类', '')])
    select.options.extend(Option('Option', category_meta.value, category_meta.key) for category_meta in
                          Meta.query_categories().order_by(Meta.value).all())
    return select


@manage.connect_via('category')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_category_name = Meta.query.get(ids[0]).value
            for category in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(category)
            db.session.commit()
            message = '已删除分类"' + first_category_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '种分类'
            flash(message)


@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['all_category_metas'] = Meta.categories()
    context['category_meta_ids'] = [category_post_meta.meta_id for category_post_meta
                                    in context['post'].category_post_metas.options(load_only('meta_id'))]
    widgets.append(os.path.join('category', 'templates', 'widget_content_category.html'))
