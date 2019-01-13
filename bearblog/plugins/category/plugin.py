from flask import flash, jsonify, redirect, request

from bearblog.plugins import current_plugin, plugin_url_for, plugin_route
from .models import Category
from bearblog.plugins.models import Plugin
from bearblog.models import Signal
from bearblog.extensions import db
from bearblog.utils import slugify


@Signal.connect('main', 'widget')
def main_widget(end_point):
    def index_url(**kwargs):
        return Signal.send('main', 'index_url', **kwargs)

    all_category = Category.query.order_by(Category.name).all()
    return {
        'slug': 'category',
        'name': '分类',
        'html': current_plugin.render_template('widget_list', 'widget.html', all_category=all_category, index_url=index_url),
        'is_html_as_list': True
    }


@current_plugin.signal.connect_this('restore')
def restore_categories(categories):
    restored_categories = []
    for category in categories:
        if type(category) is str:
            category = {'name': category}
        c = Category.query.filter_by(name=category['name']).first()
        if c is None:
            c = Category.create(name=category['name'], slug=slugify(category['name']), description=category.get('description', ''))
            db.session.add(c)
            db.session.flush()
        else:
            if c.description is None or c.description == '':
                c.description = category.get('description', '')
        restored_categories.append(c)
    db.session.flush()
    return restored_categories


@Signal.connect('article', 'restore')
def article_restore(article, data):
    if 'categories' in data:
        article.categories = current_plugin.signal.send_this('restore', categories=data['categories'])


@Signal.connect('bearblog', 'restore')
def global_restore(data):
    if 'category' in data:
        return current_plugin.signal.send_this('restore', categories=data['category'])


@Signal.connect('plugins', 'admin_sidebar_item')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '管理分类',
                'url': plugin_url_for('list', _component='admin')
            },
            {
                'type': 'link',
                'name': '新建分类',
                'url': plugin_url_for('new', _component='admin')
            }
        ]
    }


@Signal.connect('article', 'edit_widget')
def article_edit_widget(article):
    all_category = Category.query.all()
    category_ids = [category.id for category in article.categories]
    return {
        'slug': 'category',
        'name': '分类',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', all_category=all_category, category_ids=category_ids)
    }


@Signal.connect('article', 'submit_edit_widget')
def article_submit_edit_widget(slug, js_data, article):
    if slug == 'category':
        category_ids = []
        for item in js_data:
            if item['name'] == 'category-id':
                category_ids.append(int(item['value']))
        article.categories = [Category.query.get(category_id) for category_id in category_ids]


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


def admin_article_list_url(**kwargs):
    return Signal.send('article', 'admin_article_list_url', params=kwargs)


@plugin_route('/list', 'list', _component='admin')
def list_tags():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Category.query.order_by(Category.name).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        categories = pagination.items
        return current_plugin.render_template('list.html', url_for=plugin_url_for, categories=categories, pagination={'pagination': pagination, 'endpoint': 'list', 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, admin_article_list_url=admin_article_list_url)


@plugin_route('/edit', 'edit', _component='admin')
def edit_tag():
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        category = None
        if id is not None:
            category = Category.query.get(id)
        return current_plugin.render_template('edit.html', category=category)
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
        return redirect(plugin_url_for('list', _component='admin'))


@plugin_route('/new', 'new', _component='admin')
def new_tag():
    return redirect(plugin_url_for('edit', _component='admin'))


@Signal.connect('article', 'filter')
def article_filter(query, params, Article):
    if 'category' in params and params['category'] != '':
        query['query'] = query['query'].join(Article.categories).filter(Category.slug == params['category'])


def _article_meta(article):
    return current_plugin.render_template('category_items.html', categories=article.categories)


@Signal.connect('article', 'meta')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article', 'article_list_item_meta')
def article_list_item_meta(article):
    return _article_meta(article)


@Signal.connect('article', 'header_keyword')
def article_header_keyword(article):
    return [category.name for category in article.categories]


@Signal.connect('article', 'custom_list_column')
def article_custom_list_column():
    def content_func(article):
        return current_plugin.render_template('admin_category_items.html', article=article, admin_article_list_url=admin_article_list_url)

    return {
        'title': '分类',
        'item': {
            'content': content_func,
        }
    }
