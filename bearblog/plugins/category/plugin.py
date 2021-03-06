from flask import flash, jsonify, redirect, request

from bearblog.plugins import current_plugin, plugin_url_for, plugin_route
from .models import Category
from bearblog.settings import get_setting
from bearblog.models import Signal
from bearblog.extensions import db
from bearblog.utils import slugify

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@Signal.connect('widget', 'main')
def main_widget():
    def index_url(**kwargs):
        return Signal.send('index_url', 'main', **kwargs)

    all_category = Category.query.order_by(Category.name).all()
    return {
        'slug': 'category',
        'name': '分类',
        'html': current_plugin.render_template('widget_list', 'widget.html', all_category=all_category, index_url=index_url),
        'is_html_as_list': True
    }


@Signal.connect('restore')
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


@Signal.connect('restore', 'article')
def article_restore(article, data):
    if 'categories' in data:
        article.categories = Signal.send('restore', categories=data['categories'])


@Signal.connect('restore', 'bearblog')
def global_restore(data):
    if 'category' in data:
        return Signal.send('restore', categories=data['category'])


@Signal.connect('admin_sidebar_item', 'plugins')
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


@Signal.connect('edit_widget', 'article')
def article_edit_widget(article):
    all_category = Category.query.all()
    category_ids = [category.id for category in article.categories]
    return current_plugin.render_template('widget_edit_article.html', all_category=all_category, category_ids=category_ids)


@Signal.connect('get_admin_article', 'article')
def get_admin_article(article):
    return 'category', [category.id for category in article.categories]


@Signal.connect('to_json', 'article')
def article_to_json(article, level):
    return 'category', [category.to_json(level) for category in article.categories]


@Signal.connect('submit_edit_widget', 'article')
def article_submit_edit_widget(slug, js_data, article):
    if slug == 'category':
        category_ids = []
        for item in js_data:
            if item['name'] == 'category-id':
                category_ids.append(int(item['value']))
        article.categories = [Category.query.get(category_id) for category_id in category_ids]


@Signal.connect('update_article', 'article')
def update_article(article, data):
    if 'category' in data:
        article.categories = [Category.query.get(category_id) for category_id in data['category']]


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
    return Signal.send('admin_article_list_url', 'article', params=kwargs)


@plugin_route('/list', 'list', _component='admin')
def list_tags():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Category.query.order_by(Category.name).paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
        categories = pagination.items
        return current_plugin.render_template('list.html', categories=categories, pagination={'pagination': pagination, 'endpoint': 'list', 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, admin_article_list_url=admin_article_list_url)


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


@Signal.connect('filter', 'article')
def article_filter(query, params, Article):
    if 'category' in params and params['category'] != '':
        query['query'] = query['query'].join(Article.categories).filter(Category.slug == params['category'])


def _article_meta(article):
    return current_plugin.render_template('category_items.html', categories=article.categories)


@Signal.connect('meta', 'article')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article_list_item_meta', 'article')
def article_list_item_meta(article):
    return {
        'name': '分类',
        'slug': current_plugin.slug,
        'value': [category.to_json() for category in article.categories]
    }


@Signal.connect('header_keyword', 'article')
def article_header_keyword(article):
    return [category.name for category in article.categories]


@Signal.connect('custom_list_column', 'article')
def article_custom_list_column():
    def content_func(article):
        return current_plugin.render_template('admin_category_items.html', article=article, admin_article_list_url=admin_article_list_url)

    return {
        'title': '分类',
        'item': {
            'content': content_func,
        }
    }
