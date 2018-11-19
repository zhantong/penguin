from ...models import db
from .models import Tag
from flask import current_app, flash, render_template, jsonify, redirect
from ...utils import slugify
from ...signals import restore
from ..article import signals as article_signals
from ..models import Plugin
from ..article.plugin import article as article_instance
from . import signals

tag = Plugin('标签', 'tag')
tag_instance = tag


@article_signals.restore.connect
def restore_article(sender, data, article, **kwargs):
    if 'tags' in data:
        ts = []
        for tag in data['tags']:
            t = Tag.query.filter_by(name=tag).first()
            if t is None:
                t = Tag.create(name=tag, slug=slugify(tag))
                db.session.add(t)
                db.session.flush()
            ts.append(t)
        article.tags = ts
        db.session.flush()


@restore.connect
def restore(sender, data, **kwargs):
    if 'tag' in data:
        for tag in data['tag']:
            t = Tag.query.filter_by(name=tag['name']).first()
            if t is None:
                t = Tag.create(name=tag['name'], slug=slugify(tag['name']),
                               description=tag['description'])
                db.session.add(t)
                db.session.flush()
            else:
                t.description = tag['description']


@tag.route('admin', '/list', '管理标签')
def dispatch(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Tag.query.order_by(Tag.name) \
            .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        tags = pagination.items
        custom_columns = []
        column = {}
        signals.custom_list_column.send(column=column)
        custom_columns.append(column['column'])
        templates.append(render_template(tag.template_path('list.html'), tag_instance=tag, tags=tags,
                                         article_instance=article_instance,
                                         pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                                     'url_for': tag_instance.url_for}, custom_columns=custom_columns))
        scripts.append(render_template(tag.template_path('list.js.html')))


@tag.route('admin', '/edit', None)
def edit_tag(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        tag = None
        if id is not None:
            tag = Tag.query.get(id)
        templates.append(render_template(tag_instance.template_path('edit.html'), tag=tag))
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
        templates.append(redirect(tag_instance.url_for('/list')))


@tag.route('admin', '/new', '新建标签')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(tag.url_for('/edit')))


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


@article_signals.show_edit_article_widget.connect
def show_edit_article_widget(sender, post, widgets, **kwargs):
    all_tag_name = [tag.name for tag in Tag.query.all()]
    tag_names = [tag.name for tag in post.tags]
    widgets.append({
        'slug': 'tag',
        'name': '标签',
        'html': render_template(tag_instance.template_path('widget_edit_article', 'widget.html'),
                                all_tag_name=all_tag_name),
        'js': render_template(tag_instance.template_path('widget_edit_article', 'widget.js.html'),
                              tag_names=tag_names)
    })


@signals.get_widget.connect
def get_widget(sender, tags, widget, **kwargs):
    all_tag_name = [tag.name for tag in Tag.query.all()]
    tag_names = [tag.name for tag in tags]
    widget['widget'] = {
        'slug': 'tag',
        'name': '标签',
        'html': render_template(tag_instance.template_path('widget_edit_article', 'widget.html'),
                                all_tag_name=all_tag_name),
        'js': render_template(tag_instance.template_path('widget_edit_article', 'widget.js.html'),
                              tag_names=tag_names)
    }


@signals.set_widget.connect
def set_widget(sender, js_data, tags, **kwargs):
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


@signals.filter.connect
def filter(sender, query, params, join_db=Tag, **kwargs):
    if 'tag' in params and params['tag'] != '':
        query['query'] = query['query'].join(join_db).filter(Tag.slug == params['tag'])
