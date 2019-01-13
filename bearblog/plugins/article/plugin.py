import json
import os.path
import re
from datetime import datetime
from uuid import uuid4

import markdown2
from flask import request, make_response, url_for, session, flash, jsonify, send_from_directory

from bearblog.plugins import current_plugin, plugin_route, plugin_url_for
from .models import Article
from bearblog.plugins.models import Plugin
from bearblog.models import Signal, User
from bearblog.extensions import db
from bearblog import component_route, component_url_for


@component_route('/article/static/<path:filename>', 'article_static')
def article_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@component_route('/archives/<int:number>.html', 'show_article', 'main')
def show_article(number):
    def get_articles(repository_id):
        return Article.query.filter_by(repository_id=repository_id).order_by(Article.timestamp.desc()).all()

    article = Article.query.filter_by(number=number)
    if 'version' in request.args:
        article = article.filter_by(number=request.args['version'])
    article = article.first_or_404()
    cookies_to_set = {}
    metas = current_plugin.signal.send_this('meta', article=article)
    header_keywords = current_plugin.signal.send_this('header_keyword', article=article)
    widgets = current_plugin.signal.send_this('show_article_widget', session=session, article=article)
    right_widgets = widgets['right']
    left_widgets = widgets['left']
    after_article_widgets = widgets['bottom']
    current_plugin.signal.send_this('on_showing_article', article=article, request=request, cookies_to_set=cookies_to_set)
    current_plugin.signal.send_this('modify_article_when_showing', article=article)
    resp = make_response(current_plugin.render_template('article.html', article=article, after_article_widgets=after_article_widgets, left_widgets=left_widgets, right_widgets=right_widgets, get_articles=get_articles, metas=metas, header_keywords=header_keywords))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@Signal.connect('plugins', 'admin_sidebar_item')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '设置',
                'url': plugin_url_for('settings', _component='admin')
            },
            {
                'type': 'link',
                'name': '管理文章',
                'url': plugin_url_for('list', _component='admin')
            },
            {
                'type': 'link',
                'name': '撰写文章',
                'url': plugin_url_for('edit', _component='admin')
            }
        ]
    }


@Signal.connect('bearblog', 'restore')
def restore(data, directory):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], body=article['body'], timestamp=datetime.utcfromtimestamp(article['timestamp']), author=User.query.filter_by(username=article['author']).one(), repository_id=article['version']['repository_id'], status=article['version']['status'])
            db.session.add(a)
            db.session.flush()
            current_plugin.signal.send_this('restore', article=a, data=article, directory=directory)


@current_plugin.signal.connect_this('article_url')
def article_url(article, anchor):
    return component_url_for('show_article', 'main', number=article.number, _anchor=anchor)


@current_plugin.signal.connect_this('article_list_url')
def article_list_url(params):
    return url_for('.dispatch', path=current_plugin.slug + '/' + 'list', **params)


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


@plugin_route('/list', 'list', _component='admin')
def article_list():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
        else:
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

            return jsonify({'result': 'OK'})
    else:
        cleanup_temp_article()
        return current_plugin.signal.send_this('get_admin_article_list', params=request.args)


@current_plugin.signal.connect_this('get_admin_article_list')
def get_admin_widget_article_list(params):
    def get_articles(repository_id):
        return Article.query.filter_by(repository_id=repository_id).order_by(Article.version_timestamp.desc()).all()

    page = 1
    if 'page' in params:
        page = int(params['page'])
    query = db.session.query(Article.repository_id).group_by(Article.repository_id).order_by(Article.version_timestamp.desc())
    query = {'query': query}
    filter(query, request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    custom_columns = current_plugin.signal.send_this('custom_list_column')
    return current_plugin.render_template('list.html', repository_ids=repository_ids, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, get_articles=get_articles, url_for=plugin_url_for, custom_columns=custom_columns)


@plugin_route('/edit', 'edit', _component='admin')
def edit_article():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        timestamp = datetime.utcfromtimestamp(int(request.form['timestamp']))
        article = Article.query.get(int(request.form['id']))
        if article.repository_id is None:
            repository_id = str(uuid4())
        else:
            repository_id = article.repository_id
        new_article = Article(title=title, body=body, timestamp=timestamp, author=article.author, repository_id=repository_id, status='published')
        current_plugin.signal.send_this('duplicate', old_article=article, new_article=new_article)
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            current_plugin.signal.send_this('submit_edit_widget', slug=slug, js_data=js_data, article=new_article)
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
        widgets.append(current_plugin.signal.send_this('get_widget_submit', article=article))
        widgets.extend(current_plugin.signal.send_this('edit_widget', article=article))
        return current_plugin.render_template('edit.html', article=article, widgets=widgets)


def cleanup_temp_article():
    Article.query.filter_by(status='temp').delete()
    db.session.commit()


@current_plugin.signal.connect_this('get_article')
def get_article(article_id):
    return Article.query.get(article_id)


@Signal.connect('main', 'widget')
def main_widget(request):
    def get_metas(article):
        return current_plugin.signal.send_this('article_list_item_meta', article=article)

    page = request.args.get('page', 1, type=int)
    query = Article.query_published().order_by(Article.timestamp.desc())
    query = {'query': query}
    filter(query, request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
    articles = pagination.items
    return {
        'slug': 'article_list',
        'name': '文章列表',
        'html': current_plugin.render_template('widget_article_list', 'widget.html', articles=articles, pagination=pagination, request_params=request.args, get_metas=get_metas)
    }


def filter(query, params):
    if 'search' in request.args and request.args['search'] != '':
        query['query'] = query['query'].whoosh_search(request.args['search'])
    current_plugin.signal.send_this('filter', query=query, params=params, Article=Article)


@Signal.connect('main', 'navbar_item')
def navbar_item():
    return {
        'type': 'template',
        'template': current_plugin.render_template('navbar_search', 'navbar.html'),
    }


@current_plugin.signal.connect_this('admin_article_list_url')
def admin_article_list_url(params):
    return plugin_url_for('list', _component='admin', **params)


@Signal.connect('page', 'dynamic_page')
def dynamic_page():
    articles = Article.query_published().order_by(Article.timestamp.desc()).all()
    custom_columns = current_plugin.signal.send_this('custom_contents_column')
    return {
        'title': '文章目录',
        'slug': 'list',
        'html': current_plugin.render_template('dynamic_page_contents', 'contents.html', articles=articles, custom_columns=custom_columns),
        'script': current_plugin.render_template('dynamic_page_contents', 'contents.js.html'),
        'style': ''
    }


@current_plugin.signal.connect_this('get_widget_submit')
def get_widget_submit(article):
    return {
        'slug': 'submit',
        'name': '发布',
        'html': current_plugin.render_template('widget_submit', 'widget.html'),
        'footer': current_plugin.render_template('widget_submit', 'footer.html'),
        'js': current_plugin.render_template('widget_submit', 'widget.js.html', article=article)
    }


RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def on_changed_article_body(target, value, oldvalue, initiator):
    if current_plugin.signal.send_this('should_compile_markdown_when_body_change', article=target):
        extras = current_plugin.signal.send_this('markdown2_extra')
        html = markdown2.markdown(value, extras=extras)
        target.body_html = html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'
        current_plugin.signal.send_this('after_markdown_converted', article=target, html=html)


db.event.listen(Article.body, 'set', on_changed_article_body)


def _meta_publish_datetime(article):
    return current_plugin.render_template('meta_publish_datetime.html', datetime=article.timestamp)


@current_plugin.signal.connect_this('meta')
def meta_publish_datetime(article):
    return _meta_publish_datetime(article)


@current_plugin.signal.connect_this('article_list_item_meta')
def article_list_item_meta(article):
    return _meta_publish_datetime(article)


@plugin_route('/settings', 'settings', _component='admin')
def settings():
    return Signal.send('settings', 'get_rendered_settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug})
