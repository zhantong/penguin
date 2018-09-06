from ...models import db
from .models import Category
from ..post.models import Post
from flask import current_app, url_for, flash, render_template, jsonify, redirect
from ...element_models import Hyperlink, Plain, Table, Pagination, Select, Option
from sqlalchemy.orm import load_only
from ...main.signals import index
from ..post.signals import post_keywords, custom_list
from ...admin.signals import sidebar, show_list, manage, edit, submit
from ..article.signals import article_list_column_head, article_list_column, submit_article, edit_article, \
    article_search_select, article, restore_article
from ..article_list.signals import custom_article_list
from ...utils import slugify
from ...signals import restore
from ..article_list.signals import article_list_meta
from ...plugins import add_template_file
from pathlib import Path
from ..article import signals as article_signals
import os.path
from ..models import Plugin
from ..article.plugin import article as article_instance

category = Plugin('分类', 'category')
category_instance = category


@custom_article_list.connect
@custom_list.connect
def custom_list(sender, args, query):
    if 'category' in args and args['category'] != '':
        query['query'] = query['query'].join(Post.categories).filter(Category.slug == args['category'])
    return query


@article_list_column_head.connect
def article_list_column_head(sender, head):
    head.append('分类')


@article_list_column.connect
def article_list_column(sender, post, row):
    row.append([Hyperlink('Hyperlink', category.name,
                          url_for('.show_list', type='post', sub_type='article', category=category.slug)) for
                category in post.categories])


@article_search_select.connect
def article_search_select(sender, selects):
    select = Select('Select', 'category', [Option('Option', '全部分类', '')])
    select.options.extend(Option('Option', category.name, category.slug) for category in
                          Category.query.order_by(Category.name).all())
    selects.append(select)


@submit_article.connect
def submit_article(sender, form, post):
    category_ids = form.getlist('category-id')
    post.categories = [Category.query.get(category_id) for category_id in category_ids]


@index.connect
def index(sender, context, left_widgets, **kwargs):
    all_category = Category.query.order_by(Category.name).all()
    context['all_category'] = all_category
    add_template_file(left_widgets, Path(__file__), 'templates', 'main', 'widget_content.html')


@post_keywords.connect
def post_keywords(sender, post, keywords, **kwargs):
    keywords.extend(category.name for category in post.categories)


@article.connect
def article(sender, article_metas, **kwargs):
    add_template_file(article_metas, Path(__file__), 'templates', 'main', 'article_meta.html')


@restore_article.connect
def restore_article(sender, data, article, **kwargs):
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


@article_list_meta.connect
def article_list_meta(sender, metas, **kwargs):
    add_template_file(metas, Path(__file__), 'templates', 'main', 'article_list_meta.html')


@article_signals.show_edit_article_widget.connect
def show_edit_article_widget(sender, post, widgets, **kwargs):
    all_category = Category.query.all()
    category_ids = [category.id for category in post.categories]
    widgets.append({
        'slug': 'category',
        'name': '分类',
        'html': render_template(os.path.join('category', 'templates', 'widget_edit_article', 'widget.html'),
                                all_category=all_category, category_ids=category_ids)
    })


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
            render_template(os.path.join('category', 'templates', 'list.html'), category_instance=category_instance,
                            categories=categories,
                            article_instance=article_instance,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': category_instance.url_for}))
        scripts.append(render_template(os.path.join('category', 'templates', 'list.js.html')))


@category.route('admin', '/edit', None)
def edit_tag(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        category = None
        if id is not None:
            category = Category.query.get(id)
        templates.append(render_template(os.path.join('category', 'templates', 'edit.html'), category=category))
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
