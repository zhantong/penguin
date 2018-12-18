from ..models import Plugin
from ...main import main
from flask import request, make_response, url_for, session, flash, jsonify, send_from_directory
from datetime import datetime
from ...models import User
from ...models import db

from .models import Article
import json
from .. import plugin
import os.path
from uuid import uuid4
import markdown2
import re

current_plugin = Plugin.current_plugin()


@plugin.route('/article/static/<path:filename>')
def article_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


def get_metas(article):
    return current_plugin.signal.send_this('meta', article=article)


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
    cookies_to_set = {}
    metas = get_metas(article)
    header_keywords = current_plugin.signal.send_this('header_keyword', article=article)
    widget_rendered_comments = Plugin.Signal.send('comment', 'get_widget_rendered_comments', session=session, comments=article.comments, meta={'type': 'article', 'article_id': article.id})
    left_widgets.append(Plugin.Signal.send('toc', 'get_widget', article=article))
    left_widgets.append(Plugin.Signal.send('prev_next_articles', 'get_widget', article=article))
    Plugin.Signal.send('view_count', 'viewing', repository_id=article.repository_id, request=request, cookies_to_set=cookies_to_set)
    if article.template is not None:
        article.body_html = Plugin.Signal.send('template', 'render_template', template=article.template, json_params=json.loads(article.body))
    resp = make_response(current_plugin.render_template('article.html', article=article, widget_rendered_comments=widget_rendered_comments, left_widgets=left_widgets, right_widgets=right_widgets, get_articles=get_articles, metas=metas, header_keywords=header_keywords))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@Plugin.Signal.connect('app', 'restore')
def restore(sender, data, directory, **kwargs):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], body=article['body'], timestamp=datetime.utcfromtimestamp(article['timestamp']), author=User.query.filter_by(username=article['author']).one(), repository_id=article['version']['repository_id'], status=article['version']['status'])
            db.session.add(a)
            db.session.flush()
            if 'comments' in article:
                a.comments = Plugin.Signal.send('comment', 'restore', comments=article['comments'])
                db.session.flush()
            if 'attachments' in article:
                def attachment_restored(attachment, attachment_name):
                    a.body = a.body.replace(attachment['file_path'], '/attachments/' + attachment_name)
                    db.session.flush()

                a.attachments = Plugin.Signal.send('attachment', 'restore', attachments=article['attachments'], directory=directory, attachment_restored=attachment_restored)
                db.session.flush()
            if 'view_count' in article:
                Plugin.Signal.send('view_count', 'restore', repository_id=a.repository_id, count=article['view_count'])
            current_plugin.signal.send_this('restore', article=a, data=article)


@Plugin.Signal.connect('comment', 'get_comment_show_info')
def get_comment_show_info(sender, comment, anchor, **kwargs):
    if comment.article is not None:
        return {
            'title': comment.article.title,
            'url': url_for('main.show_article', number=comment.article.number, _anchor=anchor)
        }


@current_plugin.signal.connect_this('article_list_url')
def article_list_url(sender, params, **kwargs):
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


@current_plugin.route('admin', '/list', '管理文章')
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
        widget = current_plugin.signal.send_this('get_admin_article_list', params=request.args)
        templates.append(widget['html'])
        scripts.append(widget['js'])


@current_plugin.signal.connect_this('get_admin_article_list')
def get_admin_widget_article_list(sender, params, **kwargs):
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
    return {
        'html': current_plugin.render_template('list.html', repository_ids=repository_ids, pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {}, 'url_for': current_plugin.url_for}, get_articles=get_articles, url_for=current_plugin.url_for, custom_columns=custom_columns),
        'js': current_plugin.render_template('list.js.html')
    }


@current_plugin.route('admin', '/edit', '撰写文章')
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
        new_article = Article(title=title, body=body, timestamp=timestamp, author=article.author, comments=article.comments, attachments=article.attachments, repository_id=repository_id, status='published')
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            current_plugin.signal.send_this('submit_edit_widget', slug=slug, js_data=js_data, article=new_article)
            if slug == 'template':
                new_article.template = Plugin.Signal.send('template', 'set_widget', js_data=js_data)
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
        widgets.append(Plugin.Signal.send('template', 'get_widget', current_template_id=article.template_id))
        widgets.append(Plugin.Signal.send('attachment', 'get_widget', attachments=article.attachments, meta={'type': 'article', 'article_id': article.id}))
        widgets.extend(current_plugin.signal.send_this('edit_widget', article=article))
        templates.append(current_plugin.render_template('edit.html', article=article, widgets=widgets))
        scripts.append(current_plugin.render_template('edit.js.html', article=article, widgets=widgets))
        csss.append(current_plugin.render_template('edit.css.html', widgets=widgets))


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


@current_plugin.signal.connect_this('get_widget_article_list')
def get_widget_article_list(sender, request, **kwargs):
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
        'html': current_plugin.render_template('widget_article_list', 'widget.html', articles=articles, get_comment_show_info=get_comment_show_info, pagination=pagination, request_params=request.args, get_metas=get_metas)
    }


def filter(query, params):
    if 'search' in request.args and request.args['search'] != '':
        query['query'] = query['query'].whoosh_search(request.args['search'])
    current_plugin.signal.send_this('filter', query=query, params=params, Article=Article)
    Plugin.Signal.send('template', 'filter', query=query, params=params, join_db=Article.template)


@current_plugin.signal.connect_this('get_navbar_item')
def get_navbar_item(sender, **kwargs):
    return {
        'type': 'template',
        'template': current_plugin.render_template('navbar_search', 'navbar.html'),
    }


@current_plugin.signal.connect_this('admin_article_list_url')
def admin_article_list_url(sender, params, **kwargs):
    return current_plugin.url_for('/list', **params)


@Plugin.Signal.connect('template', 'custom_list_column')
def template_custom_list_column(sender, **kwargs):
    def name_func(template):
        return len(template.articles)

    def link_func(template):
        return current_plugin.url_for('/list', **template.get_info()['url_params'])

    return {
        'title': '文章数',
        'item': {
            'name': name_func,
            'link': link_func
        }
    }


@Plugin.Signal.connect('page', 'dynamic_page')
def dynamic_page(sender, **kwargs):
    articles = Article.query_published().order_by(Article.timestamp.desc()).all()
    return {
        'title': '文章目录',
        'slug': 'list',
        'html': current_plugin.render_template('dynamic_page_contents', 'contents.html', articles=articles),
        'script': current_plugin.render_template('dynamic_page_contents', 'contents.js.html'),
        'style': ''
    }


@current_plugin.signal.connect_this('get_widget_submit')
def get_widget_submit(sender, article, **kwargs):
    return {
        'slug': 'submit',
        'name': '发布',
        'html': current_plugin.render_template('widget_submit', 'widget.html'),
        'footer': current_plugin.render_template('widget_submit', 'footer.html'),
        'js': current_plugin.render_template('widget_submit', 'widget.js.html', article=article)
    }


@current_plugin.context_func
def render_num_comments(article):
    return Plugin.Signal.send('comment', 'get_rendered_num_comments', comments=article.comments)


@current_plugin.context_func
def render_view_count(article):
    return Plugin.Signal.send('view_count', 'get_rendered_view_count', view_count=article.get_view_count())


RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def on_changed_article_body(target, value, oldvalue, initiator):
    if target.template is None:
        extras = current_plugin.signal.send_this('markdown2_extra')
        html = markdown2.markdown(value, extras=extras)
        target.body_html = html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'
        current_plugin.signal.send_this('after_markdown_converted', article=target, html=html)


db.event.listen(Article.body, 'set', on_changed_article_body)
