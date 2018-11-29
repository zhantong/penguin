from ..models import Plugin

article = Plugin('文章', 'article')
article_instance = article

from . import meta
from ...main import main
from flask import render_template, request, make_response, url_for, current_app, session, flash, jsonify, \
    send_from_directory
from datetime import datetime
from ...models import User
from ...models import db

from .models import Article
import json
from .. import plugin
import os.path
from uuid import uuid4
from ...signals import restore


@plugin.route('/article/static/<path:filename>')
def article_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@main.route('/archives/<int:number>.html')
def show_article(number):
    def get_articles(repository_id):
        return Article.query.filter_by(repository_id=repository_id).order_by(Article.timestamp.desc()).all()

    article = Article.query.filter_by(number=number)
    if 'version' in request.args:
        article = article.filter_by(number=request.args['version'])
    article = article.first_or_404()
    left_widgets = []
    right_widgets = []
    scripts = []
    styles = []
    cookies_to_set = {}
    rendered_comments = {}
    Plugin.Signal.send('comment', 'get_rendered_comments', session=session, comments=article.comments,
                       rendered_comments=rendered_comments,
                       scripts=scripts, styles=styles,
                       meta={'type': 'article', 'article_id': article.id})
    rendered_comments = rendered_comments['rendered_comments']
    article_instance.signal.send_this('show', request=request, article=article, cookies_to_set=cookies_to_set,
                                      left_widgets=left_widgets,
                                      right_widgets=right_widgets, scripts=scripts, styles=styles)
    Plugin.Signal.send('view_count', 'viewing', repository_id=article.repository_id, request=request,
                       cookies_to_set=cookies_to_set)
    if article.template is not None:
        html = {}
        Plugin.Signal.send('template', 'render_template', template=article.template,
                           json_params=json.loads(article.body),
                           html=html)
        article.body_html = html['html']
    resp = make_response(render_template(article_instance.template_path('article.html'), article=article,
                                         rendered_comments=rendered_comments, left_widgets=left_widgets,
                                         right_widgets=right_widgets, scripts=scripts, styles=styles,
                                         get_articles=get_articles))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@restore.connect
def restore(sender, data, directory, **kwargs):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], body=article['body'],
                        timestamp=datetime.utcfromtimestamp(article['timestamp']),
                        author=User.query.filter_by(username=article['author']).one(),
                        repository_id=article['version']['repository_id'], status=article['version']['status'])
            db.session.add(a)
            db.session.flush()
            if 'comments' in article:
                restored_comments = []
                Plugin.Signal.send('comment', 'restore', comments=article['comments'],
                                   restored_comments=restored_comments)
                a.comments = restored_comments
                db.session.flush()
            if 'attachments' in article:
                def attachment_restored(attachment, attachment_name):
                    a.body = a.body.replace(attachment['file_path'], '/attachments/' + attachment_name)
                    db.session.flush()

                restored_attachments = []
                Plugin.Signal.send('attachment', 'restore', attachments=article['attachments'], directory=directory,
                                   restored_attachments=restored_attachments,
                                   attachment_restored=attachment_restored)
                a.attachments = restored_attachments
                db.session.flush()
            if 'view_count' in article:
                Plugin.Signal.send('view_count', 'restore', repository_id=a.repository_id,
                                   count=article['view_count'])
            if 'categories' in article:
                restored_categories = []
                Plugin.Signal.send('category', 'restore', categories=article['categories'],
                                   restored_categories=restored_categories)
                a.categories = restored_categories
                db.session.flush()
            if 'tags' in article:
                restored_tags = []
                Plugin.Signal.send('tag', 'restore', tags=article['tags'], restored_tags=restored_tags)
                a.tags = restored_tags
                db.session.flush()


@Plugin.Signal.connect('comment', 'get_comment_show_info')
def get_comment_show_info(sender, comment, anchor, info, **kwargs):
    if comment.article is not None:
        info['title'] = comment.article.title
        info['url'] = url_for('main.show_article', number=comment.article.number, _anchor=anchor)


@article_instance.signal.connect_this('article_list_url')
def article_list_url(sender, params, **kwargs):
    return url_for('.dispatch', path=meta.PLUGIN_NAME + '/' + 'list', **params)


def delete(article_id):
    article = Article.query.get(article_id)
    article_title = article.title
    db.session.delete(article)
    db.session.commit()
    message = '已删除文章"' + article_title + '"'
    flash(message)
    return {
        'result': 'OK'
    }


@article.route('admin', '/list', '管理文章')
def article_list(request, templates, meta, scripts, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
        else:
            meta['override_render'] = True

            article_id = request.form['id']
            action = request.form['action']
            article = Article.query.get(article_id)
            if action == 'publish':
                article.status = 'published'
            elif action == 'archive':
                article.status = 'archived'
            elif action == 'draft':
                article.status = 'draft'
            elif action == 'hide':
                article.status = 'hidden'
            db.session.commit()

            templates.append(jsonify({'result': 'OK'}))
    else:
        cleanup_temp_article()
        widget = {}
        article_instance.signal.send_this('get_admin_article_list', widget=widget, params=request.args)
        widget = widget['widget']
        templates.append(widget['html'])
        scripts.append(widget['js'])


@article_instance.signal.connect_this('get_admin_article_list')
def get_admin_widget_article_list(sender, widget, params, **kwargs):
    def get_articles(repository_id):
        return Article.query.filter_by(repository_id=repository_id).order_by(Article.version_timestamp.desc()).all()

    page = 1
    if 'page' in params:
        page = int(params['page'])
    query = db.session.query(Article.repository_id).group_by(Article.repository_id).order_by(
        Article.version_timestamp.desc())
    query = {'query': query}
    article_instance.signal.send_this('filter', query=query, params=request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    widget['widget'] = {
        'html': render_template(article_instance.template_path('list.html'), repository_ids=repository_ids,
                                pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                            'url_for': article_instance.url_for},
                                get_articles=get_articles,
                                url_for=article_instance.url_for),
        'js': render_template(article_instance.template_path('list.js.html'))
    }


@article.route('admin', '/edit', '撰写文章')
def edit_article(request, templates, scripts, csss, **kwargs):
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        timestamp = datetime.utcfromtimestamp(int(request.form['timestamp']))
        article = Article.query.get(int(request.form['id']))
        if article.repository_id is None:
            repository_id = str(uuid4())
        else:
            repository_id = article.repository_id
        new_article = Article(title=title, body=body, timestamp=timestamp, author=article.author,
                              comments=article.comments, attachments=article.attachments, repository_id=repository_id,
                              status='published')
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            if slug == 'category':
                categories = []
                Plugin.Signal.send('category', 'set_widget', js_data=js_data, categories=categories)
                new_article.categories = categories
            if slug == 'tag':
                tags = []
                Plugin.Signal.send('tag', 'set_widget', js_data=js_data, tags=tags)
                new_article.tags = tags
            if slug == 'template':
                template = {}
                Plugin.Signal.send('template', 'set_widget', js_data=js_data, template=template)
                new_article.template = template['template']
        db.session.add(new_article)
        db.session.commit()
    else:
        cleanup_temp_article()
        if 'id' in request.args:
            article = Article.query.get(int(request.args['id']))
        else:
            article = Article(status='temp')
            db.session.add(article)
            db.session.commit()
        widgets = []
        # signals.show_edit_article_widget.send(request=request, article=article, widgets=widgets)
        widget = {'widget': None}
        Plugin.Signal.send('template', 'get_widget', current_template_id=article.template_id, widget=widget)
        widgets.append(widget['widget'])
        Plugin.Signal.send('attachment', 'get_widget', attachments=article.attachments,
                           meta={'type': 'article', 'article_id': article.id}, widget=widget)
        widgets.append(widget['widget'])
        Plugin.Signal.send('category', 'get_widget', categories=article.categories, widget=widget)
        widgets.append(widget['widget'])
        Plugin.Signal.send('tag', 'get_widget', tags=article.tags, widget=widget)
        widgets.append(widget['widget'])
        templates.append(
            render_template(article_instance.template_path('edit.html'), article=article, widgets=widgets))
        scripts.append(
            render_template(article_instance.template_path('edit.js.html'), article=article, widgets=widgets))
        csss.append(render_template(article_instance.template_path('edit.css.html'), widgets=widgets))


def cleanup_temp_article():
    Article.query.filter_by(status='temp').delete()
    db.session.commit()


@Plugin.Signal.connect('comment', 'on_new_comment')
def on_new_comment(sender, comment, meta, **kwargs):
    if 'type' in meta and meta['type'] == 'article':
        article_id = int(meta['article_id'])
        article = Article.query.get(article_id)
        article.comments.append(comment)
        db.session.commit()


@Plugin.Signal.connect('attachment', 'on_new_attachment')
def on_new_attachment(sender, attachment, meta, **kwargs):
    if 'type' in meta and meta['type'] == 'article':
        article_id = int(meta['article_id'])
        article = Article.query.get(article_id)
        article.attachments.append(attachment)
        db.session.commit()


@article_instance.signal.connect_this('get_widget_category_list')
def get_widget_category_list(sender, widget, **kwargs):
    def count_func(category):
        return len(category.articles)

    Plugin.Signal.send('category', 'get_widget_list', widget=widget, end_point='.index', count_func=count_func)


@article_instance.signal.connect_this('get_widget_article_list')
def get_widget_article_list(sender, widget, request, **kwargs):
    page = request.args.get('page', 1, type=int)
    query = Article.query_published().order_by(Article.timestamp.desc())
    query = {'query': query}
    article_instance.signal.send_this('filter', query=query, params=request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    articles = pagination.items
    widget['widget'] = {
        'slug': 'article_list',
        'name': '文章列表',
        'html': render_template(article_instance.template_path('widget_article_list', 'widget.html'),
                                articles=articles, get_comment_show_info=get_comment_show_info, pagination=pagination,
                                request_params=request.args)
    }


@article_instance.signal.connect_this('filter')
def filter(sender, query, params, **kwargs):
    if 'search' in request.args and request.args['search'] != '':
        query['query'] = query['query'].whoosh_search(request.args['search'])
    Plugin.Signal.send('category', 'filter', query=query, params=params, join_db=Article.categories)
    Plugin.Signal.send('tag', 'filter', query=query, params=params, join_db=Article.tags)
    Plugin.Signal.send('template', 'filter', query=query, params=params, join_db=Article.template)


@article_instance.signal.connect_this('get_navbar_item')
def get_navbar_item(sender, item, **kwargs):
    item['item'] = {
        'type': 'template',
        'template': render_template(article_instance.template_path('navbar_search', 'navbar.html')),
    }


@Plugin.Signal.connect('category', 'custom_list_column')
def category_custom_list_column(sender, column, **kwargs):
    def name_func(category):
        return len(category.articles)

    def link_func(category):
        return article_instance.url_for('/list', **category.get_info()['url_params'])

    column['column'] = {
        'title': '文章数',
        'item': {
            'name': name_func,
            'link': link_func
        }
    }


@Plugin.Signal.connect('tag', 'custom_list_column')
def tag_custom_list_column(sender, column, **kwargs):
    def name_func(tag):
        return len(tag.articles)

    def link_func(tag):
        return article_instance.url_for('/list', **tag.get_info()['url_params'])

    column['column'] = {
        'title': '文章数',
        'item': {
            'name': name_func,
            'link': link_func
        }
    }


@Plugin.Signal.connect('template', 'custom_list_column')
def template_custom_list_column(sender, custom_columns, **kwargs):
    def name_func(template):
        return len(template.articles)

    def link_func(template):
        return article_instance.url_for('/list', **template.get_info()['url_params'])

    custom_columns.append({
        'title': '文章数',
        'item': {
            'name': name_func,
            'link': link_func
        }
    })


@Plugin.Signal.connect('page', 'dynamic_page')
def dynamic_page(sender, pages, **kwargs):
    articles = Article.query_published().order_by(Article.timestamp.desc()).all()
    pages.append({
        'title': '文章目录',
        'slug': 'list',
        'html': render_template(article_instance.template_path('dynamic_page_contents', 'contents.html'),
                                articles=articles),
        'script': render_template(article_instance.template_path('dynamic_page_contents', 'contents.js.html')),
        'style': ''
    })
