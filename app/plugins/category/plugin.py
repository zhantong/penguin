from ...models import db
from .models import Category
from flask import current_app, flash, render_template, jsonify, redirect
from ...utils import slugify
from ...signals import restore
from ..article import signals as article_signals
from ..models import Plugin
from ..article.plugin import article as article_instance
from . import signals

category = Plugin('分类', 'category')
category_instance = category


@signals.get_widget_list.connect
def get_widget_list(sender, widget, end_point, count_func, **kwargs):
    all_category = Category.query.order_by(Category.name).all()
    widget['widget'] = {
        'slug': 'category',
        'name': '分类',
        'html': render_template(category_instance.template_path('widget_list', 'widget.html'),
                                all_category=all_category, end_point=end_point, count_func=count_func)
    }


@article_signals.restore.connect
def article_restore(sender, data, article, **kwargs):
    if 'categories' in data:
        cs = []
        for category in data['categories']:
            c = Category.query.filter_by(name=category).first()
            if c is None:
                c = Category.create(name=category, slug=slugify(category))
                db.session.add(c)
                db.session.flush()
            cs.append(c)
        article.categories = cs
        db.session.flush()


@restore.connect
def restore(sender, data, **kwargs):
    if 'category' in data:
        for category in data['category']:
            c = Category.query.filter_by(name=category['name']).first()
            if c is None:
                c = Category.create(name=category['name'], slug=slugify(category['name']),
                                    description=category['description'])
                db.session.add(c)
                db.session.flush()
            else:
                c.description = category['description']


@article_signals.show_edit_article_widget.connect
def show_edit_article_widget(sender, post, widgets, **kwargs):
    all_category = Category.query.all()
    category_ids = [category.id for category in post.categories]
    widgets.append({
        'slug': 'category',
        'name': '分类',
        'html': render_template(category_instance.template_path('widget_edit_article', 'widget.html'),
                                all_category=all_category, category_ids=category_ids)
    })


@signals.get_widget.connect
def get_widget(sender, categories, widget, **kwargs):
    all_category = Category.query.all()
    category_ids = [category.id for category in categories]
    widget['widget'] = {
        'slug': 'category',
        'name': '分类',
        'html': render_template(category_instance.template_path('widget_edit_article', 'widget.html'),
                                all_category=all_category, category_ids=category_ids)
    }


@signals.set_widget.connect
def set_widget(sender, js_data, categories, **kwargs):
    category_ids = []
    for item in js_data:
        if item['name'] == 'category-id':
            category_ids.append(int(item['value']))
    categories.extend(Category.query.get(category_id) for category_id in category_ids)


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


@category.route('admin', '/list', '管理分类')
def list_tags(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Category.query.order_by(Category.name) \
            .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        categories = pagination.items
        templates.append(
            render_template(category_instance.template_path('list.html'), category_instance=category_instance,
                            categories=categories,
                            article_instance=article_instance,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': category_instance.url_for}))
        scripts.append(render_template(category_instance.template_path('list.js.html')))


@category.route('admin', '/edit', None)
def edit_tag(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        category = None
        if id is not None:
            category = Category.query.get(id)
        templates.append(render_template(category_instance.template_path('edit.html'), category=category))
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
        templates.append(redirect(category_instance.url_for('/list')))


@category.route('admin', '/new', '新建分类')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(category_instance.url_for('/edit')))


@signals.filter.connect
def filter(sender, query, params, **kwargs):
    if 'category' in params and params['category'] != '':
        query['query'] = query['query'].filter(Category.slug == params['category'])
