from ...models import db
from .models import Tag
from flask import flash, jsonify, redirect
from ...utils import slugify
from ..models import Plugin

current_plugin = Plugin.current_plugin()


@current_plugin.signal.connect_this('restore')
def restore_tags(sender, tags, **kwargs):
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


@Plugin.Signal.connect('article', 'restore')
def article_restore(sender, article, data, **kwargs):
    if 'tags' in data:
        article.tags = current_plugin.signal.send_this('restore', tags=data['tags'])


@Plugin.Signal.connect('app', 'restore')
def global_restore(sender, data, **kwargs):
    if 'tag' in data:
        current_plugin.signal.send_this('restore', tags=data['tag'], restored_tags=[])


def admin_article_list_url(**kwargs):
    return Plugin.Signal.send('article', 'admin_article_list_url', params=kwargs)


@current_plugin.route('admin', '/list', '管理标签')
def dispatch(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Tag.query.order_by(Tag.name).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        tags = pagination.items
        templates.append(current_plugin.render_template('list.html', tag_instance=current_plugin, tags=tags, pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {}, 'url_for': current_plugin.url_for}, admin_article_list_url=admin_article_list_url))
        scripts.append(current_plugin.render_template('list.js.html'))


@current_plugin.route('admin', '/edit', None)
def edit_tag(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        tag = None
        if id is not None:
            tag = Tag.query.get(id)
        templates.append(current_plugin.render_template('edit.html', tag=tag))
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
        meta['override_render'] = True
        templates.append(redirect(current_plugin.url_for('/list')))


@current_plugin.route('admin', '/new', '新建标签')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(current_plugin.url_for('/edit')))


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


@Plugin.Signal.connect('article', 'edit_widget')
def article_edit_widget(sender, article, **kwargs):
    all_tag_name = [tag.name for tag in Tag.query.all()]
    tag_names = [tag.name for tag in article.tags]
    return {
        'slug': 'tag',
        'name': '标签',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', all_tag_name=all_tag_name),
        'js': current_plugin.render_template('widget_edit_article', 'widget.js.html', tag_names=tag_names)
    }


@Plugin.Signal.connect('article', 'submit_edit_widget')
def article_submit_edit_widget(sender, slug, js_data, article, **kwargs):
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


@Plugin.Signal.connect('article', 'filter')
def article_filter(sender, query, params, Article, **kwargs):
    if 'tag' in params and params['tag'] != '':
        query['query'] = query['query'].join(Article.tags).filter(Tag.slug == params['tag'])


def _article_meta(article):
    return current_plugin.render_template('tag_items.html', tags=article.tags)


@Plugin.Signal.connect('article', 'meta')
def article_meta(sender, article, **kwargs):
    return _article_meta(article)


@Plugin.Signal.connect('article', 'article_list_item_meta')
def article_list_item_meta(sender, article, **kwargs):
    return _article_meta(article)


@Plugin.Signal.connect('article', 'custom_list_column')
def article_custom_list_column(sender, **kwargs):
    def content_func(article):
        return current_plugin.render_template('admin_tag_items.html', article=article, admin_article_list_url=admin_article_list_url)

    return {
        'title': '标签',
        'item': {
            'content': content_func,
        }
    }


@Plugin.Signal.connect('article', 'header_keyword')
def article_header_keyword(sender, article, **kwargs):
    return [tag.name for tag in article.tags]
