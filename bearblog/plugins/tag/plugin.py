from flask import flash, jsonify, redirect, request

from bearblog.plugins import current_plugin, Plugin, plugin_route, plugin_url_for
from .models import Tag
from bearblog.models import Signal
from bearblog.extensions import db
from bearblog.utils import slugify

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@Signal.connect('restore')
def restore_tags(tags):
    restored_tags = []
    for tag in tags:
        if type(tag) is str:
            tag = {'name': tag}
        t = Tag.query.filter_by(name=tag['name']).first()
        if t is None:
            t = Tag.create(name=tag['name'], slug=slugify(tag['name']), description=tag.get('description', ''))
            db.session.add(t)
            db.session.flush()
        else:
            if t.description is None or t.description == '':
                t.description = tag.get('description', '')
        restored_tags.append(t)
    db.session.flush()
    return restored_tags


@Signal.connect('restore', 'article')
def article_restore(article, data):
    if 'tags' in data:
        article.tags = Signal.send('restore', tags=data['tags'])


@Signal.connect('restore', 'bearblog')
def global_restore(data):
    if 'tag' in data:
        Signal.send('restore', tags=data['tag'], restored_tags=[])


@Signal.connect('admin_sidebar_item', 'plugins')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '新建标签',
                'url': plugin_url_for('new', _component='admin')
            },
            {
                'type': 'link',
                'name': '管理标签',
                'url': plugin_url_for('list', _component='admin')
            }
        ]
    }


def admin_article_list_url(**kwargs):
    return Signal.send('admin_article_list_url', 'article', params=kwargs)


@plugin_route('/list', 'list', _component='admin')
def dispatch():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Tag.query.order_by(Tag.name).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        tags = pagination.items
        return current_plugin.render_template('list.html', tags=tags, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, admin_article_list_url=admin_article_list_url)


@plugin_route('/edit', 'edit', _component='admin')
def edit_tag():
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        tag = None
        if id is not None:
            tag = Tag.query.get(id)
        return current_plugin.render_template('edit.html', tag=tag)
    else:
        id = request.form.get('id', type=int)
        if id is None:
            tag = Tag()
        else:
            tag = Tag.query.get(id)
        tag.name = request.form['name']
        tag.slug = request.form['slug']
        tag.description = request.form['description']
        if tag.id is None:
            db.session.add(tag)
        db.session.commit()
        return redirect(plugin_url_for('list', _component='admin'))


@plugin_route('/new', 'new', _component='admin')
def new_tag():
    return redirect(plugin_url_for('edit', _component='admin'))


def delete(tag_id):
    tag = Tag.query.get(tag_id)
    tag_name = tag.name
    db.session.delete(tag)
    db.session.commit()
    message = '已删除标签"' + tag_name + '"'
    flash(message)
    return {
        'result': 'OK'
    }


@Signal.connect('edit_widget', 'article')
def article_edit_widget(article):
    all_tag_name = [tag.name for tag in Tag.query.all()]
    tag_names = [tag.name for tag in article.tags]
    return {
        'slug': 'tag',
        'name': '标签',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', all_tag_name=all_tag_name),
        'js': current_plugin.render_template('widget_edit_article', 'widget.js.html', tag_names=tag_names)
    }


@Signal.connect('submit_edit_widget', 'article')
def article_submit_edit_widget(slug, js_data, article):
    if slug == 'tag':
        tags = []
        tag_names = []
        for item in js_data:
            if item['name'] == 'tag_name':
                tag_names.append(item['value'])
        tag_names = set(tag_names)
        for tag_name in tag_names:
            tag = Tag.query.filter_by(name=tag_name).first()
            if tag is None:
                tag = Tag(name=tag_name, slug=slugify(tag_name))
                db.session.add(tag)
                db.session.flush()
            tags.append(tag)
        article.tags = tags


@Signal.connect('filter', 'article')
def article_filter(query, params, Article):
    if 'tag' in params and params['tag'] != '':
        query['query'] = query['query'].join(Article.tags).filter(Tag.slug == params['tag'])


def _article_meta(article):
    return current_plugin.render_template('tag_items.html', tags=article.tags)


@Signal.connect('meta', 'article')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article_list_item_meta', 'article')
def article_list_item_meta(article):
    return _article_meta(article)


@Signal.connect('custom_list_column', 'article')
def article_custom_list_column():
    def content_func(article):
        return current_plugin.render_template('admin_tag_items.html', article=article, admin_article_list_url=admin_article_list_url)

    return {
        'title': '标签',
        'item': {
            'content': content_func,
        }
    }


@Signal.connect('header_keyword', 'article')
def article_header_keyword(article):
    return [tag.name for tag in article.tags]
