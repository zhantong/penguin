from ...models import db
from .models import Tag
from ..post.models import Post
from flask import current_app, url_for, flash, render_template, jsonify, redirect
from ...element_models import Hyperlink
from ...utils import slugify
from ..post.signals import post_keywords
from ...admin.signals import submit
from ..article.signals import submit_article, edit_article, article, restore_article
from ...signals import restore
from ...plugins import add_template_file
from pathlib import Path
import os.path
from ..article import signals as article_signals
from ..Plugin import Plugin
from ..article.plugin import article as article_instance

tag = Plugin('标签', 'tag')


@article_signals.custom_list.connect
def custom_list(sender, request, query_wrap, **kwargs):
    if 'tag' in request.args and request.args['tag'] != '':
        query_wrap['query'] = query_wrap['query'].join(Post.tags).filter(Tag.slug == request.args['tag'])


@article_signals.list_column_head.connect
def article_list_column_head(sender, head, **kwargs):
    head.append('标签')


@article_signals.list_column.connect
def article_list_column(sender, article, row, **kwargs):
    row.append([Hyperlink('Hyperlink', tag.name,
                          url_for('.show_list', type='post', sub_type='article', tag=tag.slug)) for tag in
                article.tags])


@edit_article.connect
def edit_article(sender, context, widgets, scripts, **kwargs):
    context['all_tag_name'] = [tag.name for tag in Tag.query.all()]
    context['tag_names'] = [tag.name for tag in context['post'].tags]
    add_template_file(widgets, Path(__file__), 'templates', 'widget_content_tag.html')
    add_template_file(scripts, Path(__file__), 'templates', 'widget_script_tag.html')


@submit_article.connect
def submit_article(sender, form, post):
    tag_names = form.getlist('tag-name')
    tag_names = set(tag_names)
    tags = []
    for tag_name in tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag is None:
            tag = Tag(name=tag_name, slug=slugify(tag_name))
            db.session.add(tag)
            db.session.flush()
        tags.append(tag)
    post.tags = tags


@submit.connect_via('tag')
def submit(sender, args, form, **kwargs):
    id = form.get('id', type=int)
    if id is None:
        tag = Tag()
    else:
        tag = Tag.query.get(id)
    tag.name = form['name']
    tag.slug = form['slug']
    tag.description = form['description']
    if tag.id is None:
        db.session.add(tag)
    db.session.commit()


@post_keywords.connect
def post_keywords(sender, post, keywords, **kwargs):
    keywords.extend(category.name for category in post.categories)


@article.connect
def article(sender, article_metas, **kwargs):
    add_template_file(article_metas, Path(__file__), 'templates', 'main', 'article_meta.html')


@restore_article.connect
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
        templates.append(render_template(os.path.join('tag', 'templates', 'list.html'), tag_instance=tag, tags=tags,
                                         article_instance=article_instance))
        scripts.append(render_template(os.path.join('tag', 'templates', 'list.js.html')))


@tag.route('admin', '/edit', None)
def edit_tag(request, templates, **kwargs):
    id = request.args.get('id', type=int)
    tag = None
    if id is not None:
        tag = Tag.query.get(id)
    templates.append(render_template(os.path.join('tag', 'templates', 'edit.html'), tag=tag))


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
