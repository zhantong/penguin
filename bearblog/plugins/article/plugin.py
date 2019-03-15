import json
import os.path
import re
from datetime import datetime
from uuid import uuid4

import mistune
from flask import request, url_for, flash, jsonify, send_from_directory

from bearblog.plugins import current_plugin, plugin_route, plugin_url_for
from .models import Article
from bearblog.models import Signal, User
from bearblog.extensions import db
from bearblog import component_route, component_url_for
from bearblog.settings import get_setting

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/article/static/<path:filename>', 'article_static')
def article_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@Signal.connect('admin_sidebar_item', 'plugins')
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


@Signal.connect('restore', 'bearblog')
def restore(data, directory):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], body=article['body'], timestamp=datetime.utcfromtimestamp(article['timestamp']), author=User.query.filter_by(username=article['author']).one(), repository_id=article['version']['repository_id'], status=article['version']['status'])
            db.session.add(a)
            db.session.flush()
            Signal.send('restore', article=a, data=article, directory=directory)


@Signal.connect('article_url')
def article_url(article, anchor, **kwargs):
    return component_url_for('show_article', 'main', number=article.number, _anchor=anchor, **kwargs)


@Signal.connect('article_list_url')
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
        return Signal.send('get_admin_article_list', params=request.args)


@Signal.connect('get_admin_article_list')
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
    pagination = query.paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    custom_columns = Signal.send('custom_list_column')
    return current_plugin.render_template('list.html', repository_ids=repository_ids, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, get_articles=get_articles, custom_columns=custom_columns)


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
        Signal.send('duplicate', old_article=article, new_article=new_article)
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            Signal.send('submit_edit_widget', slug=slug, js_data=js_data, article=new_article)
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
        widgets.extend(Signal.send('edit_widget', article=article))
        return current_plugin.render_template('edit.html', article=article, widgets=widgets)


def cleanup_temp_article():
    Article.query.filter_by(status='temp').delete()
    db.session.commit()


@Signal.connect('get_article')
def get_article(article_id):
    return Article.query.get(article_id)


def filter(query, params):
    if 'search' in request.args and request.args['search'] != '':
        query['query'] = query['query'].whoosh_search(request.args['search'])
    Signal.send('filter', query=query, params=params, Article=Article)


@Signal.connect('navbar_item', 'main')
def navbar_item():
    return {
        'type': 'template',
        'template': current_plugin.render_template('navbar_search', 'navbar.html'),
    }


@Signal.connect('admin_article_list_url')
def admin_article_list_url(params):
    return plugin_url_for('list', _component='admin', **params)


@Signal.connect('dynamic_page', 'page')
def dynamic_page():
    articles = Article.query_published().order_by(Article.timestamp.desc()).all()
    custom_columns = Signal.send('custom_contents_column')
    return {
        'title': '文章目录',
        'slug': 'list',
        'html': current_plugin.render_template('dynamic_page_contents', 'contents.html', articles=articles, custom_columns=custom_columns),
        'script': current_plugin.render_template('dynamic_page_contents', 'contents.js.html'),
        'style': ''
    }


@Signal.connect('edit_widget')
def edit_widget_submit(article):
    return current_plugin.render_template('widget_submit.html', article=article)


RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def on_changed_article_body(target, value, oldvalue, initiator):
    class Renderer(mistune.Renderer):
        def __init__(self):
            super().__init__()
            self.toc_count = 0

        def header(self, text, level, raw=None):
            rv = '<h%d id="toc-%d">%s</h%d>\n' % (
                level, self.toc_count, text, level
            )
            self.toc_count += 1
            return rv

    renderer = Renderer()
    markdown = mistune.Markdown(renderer=renderer)

    if Signal.send('should_compile_markdown_when_body_change', article=target):
        html = markdown(value)
        target.body_html = html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'
        Signal.send('after_markdown_converted', article=target, html=html)


db.event.listen(Article.body, 'set', on_changed_article_body)


def _meta_publish_datetime(article):
    return current_plugin.render_template('meta_publish_datetime.html', datetime=article.timestamp)


@Signal.connect('meta')
def meta_publish_datetime(article):
    return _meta_publish_datetime(article)


@plugin_route('/settings', 'settings', _component='admin')
def settings():
    return Signal.send('get_rendered_settings', 'settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug}, signals=current_plugin.signal.signals)
