from ...models import db
from .models import Category
from flask import flash, render_template, jsonify, redirect
from ...utils import slugify
from ..models import Plugin

current_plugin = Plugin.current_plugin()

current_plugin.signal.declare_signal('get_widget_list', return_type='single')
current_plugin.signal.declare_signal('restore', return_type='single')
current_plugin.signal.declare_signal('set_widget', return_type='single')
current_plugin.signal.declare_signal('custom_list_column', return_type='list')
current_plugin.signal.declare_signal('get_widget', return_type='single')


@current_plugin.signal.connect_this('get_widget_list')
def get_widget_list(sender, end_point, count_func, **kwargs):
    all_category = Category.query.order_by(Category.name).all()
    return {
        'slug': 'category',
        'name': '分类',
        'html': render_template(current_plugin.template_path('widget_list', 'widget.html'),
                                all_category=all_category, end_point=end_point, count_func=count_func)
    }


@current_plugin.signal.connect_this('restore')
def restore_categories(sender, categories, **kwargs):
    restored_categories = []
    for category in categories:
        if type(category) is str:
            category = {'name': category}
        c = Category.query.filter_by(name=category['name']).first()
        if c is None:
            c = Category.create(name=category['name'], slug=slugify(category['name']),
                                description=category.get('description', ''))
            db.session.add(c)
            db.session.flush()
        else:
            if c.description is None or c.description == '':
                c.description = category.get('description', '')
        restored_categories.append(c)
    db.session.flush()
    return restored_categories


@Plugin.Signal.connect('app', 'restore')
def global_restore(sender, data, **kwargs):
    if 'category' in data:
        return current_plugin.signal.send_this('restore', categories=data['category'])


@current_plugin.signal.connect_this('get_widget')
def get_widget(sender, categories, **kwargs):
    all_category = Category.query.all()
    category_ids = [category.id for category in categories]
    return {
        'slug': 'category',
        'name': '分类',
        'html': render_template(current_plugin.template_path('widget_edit_article', 'widget.html'),
                                all_category=all_category, category_ids=category_ids)
    }


@current_plugin.signal.connect_this('set_widget')
def set_widget(sender, js_data, **kwargs):
    category_ids = []
    for item in js_data:
        if item['name'] == 'category-id':
            category_ids.append(int(item['value']))
    return [Category.query.get(category_id) for category_id in category_ids]


def delete(category_id):
    category = Category.query.get(category_id)
    category_name = category.name
    db.session.delete(category)
    db.session.commit()
    message = '已删除分类"' + category_name + '"'
    flash(message)
    return {
        'result': 'OK'
    }


@current_plugin.route('admin', '/list', '管理分类')
def list_tags(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Category.query.order_by(Category.name) \
            .paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        categories = pagination.items
        custom_columns = current_plugin.signal.send_this('custom_list_column')
        templates.append(
            render_template(current_plugin.template_path('list.html'), category_instance=current_plugin,
                            categories=categories,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': current_plugin.url_for}, custom_columns=custom_columns))
        scripts.append(render_template(current_plugin.template_path('list.js.html')))


@current_plugin.route('admin', '/edit', None)
def edit_tag(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        category = None
        if id is not None:
            category = Category.query.get(id)
        templates.append(render_template(current_plugin.template_path('edit.html'), category=category))
    else:
        id = request.form.get('id', type=int)
        if id is None:
            category = Category()
        else:
            category = Category.query.get(id)
        category.name = request.form['name']
        category.slug = request.form['slug']
        category.description = request.form['description']
        if category.id is None:
            db.session.add(category)
        db.session.commit()
        meta['override_render'] = True
        templates.append(redirect(current_plugin.url_for('/list')))


@current_plugin.route('admin', '/new', '新建分类')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(current_plugin.url_for('/edit')))


@current_plugin.signal.connect_this('filter')
def filter(sender, query, params, join_db=Category, **kwargs):
    if 'category' in params and params['category'] != '':
        query['query'] = query['query'].join(join_db).filter(Category.slug == params['category'])
