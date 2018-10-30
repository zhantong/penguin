from ..models import Plugin

article = Plugin('文章', 'article')
article_instance = article

from . import signals, meta
from ...main import main
from flask import render_template, request, make_response, redirect, url_for, current_app, session, flash, jsonify, \
    send_from_directory
from ...admin.signals import sidebar
from ...signals import restore
from datetime import datetime
from ...models import User
from ...models import db
from ...plugins import add_template_file
from pathlib import Path

from .models import Article
from ..comment import signals as comment_signals
from ..attachment import signals as attachment_signals
from ..category import signals as category_signals
from ..tag import signals as tag_signals
import json
from ..article_count.models import ArticleCount
from .. import plugin
import os.path
from uuid import uuid4


@plugin.route('/article/static/<path:filename>')
def article_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@main.route('/archives/')
def show_none_post():
    pass


@main.route('/archives/<string:slug>.html')
def show_article(slug):
    article = Article.query.filter_by(slug=slug).first_or_404()
    left_widgets = []
    right_widgets = []
    scripts = []
    styles = []
    cookies_to_set = {}
    rendered_comments = {}
    comment_signals.get_rendered_comments.send(session=session, comments=article.comments,
                                               rendered_comments=rendered_comments,
                                               scripts=scripts, styles=styles,
                                               meta={'type': 'article', 'article_id': article.id})
    rendered_comments = rendered_comments['rendered_comments']
    signals.show.send(request=request, article=article, cookies_to_set=cookies_to_set, left_widgets=left_widgets,
                      right_widgets=right_widgets, scripts=scripts, styles=styles)
    resp = make_response(render_template(Path('article', 'templates', 'article.html').as_posix(), article=article,
                                         rendered_comments=rendered_comments, left_widgets=left_widgets,
                                         right_widgets=right_widgets, scripts=scripts, styles=styles))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@main.route('/a/<int:number>')
def show_article_by_number(number):
    slug = Article.query.filter_by(number=number).first_or_404().slug
    return redirect(url_for('.show_article', slug=slug))


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@restore.connect
def restore(sender, data, directory, **kwargs):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], slug=article['slug'], body=article['body'],
                        timestamp=datetime.utcfromtimestamp(article['timestamp']),
                        author=User.query.filter_by(username=article['author']).one(),
                        repository_id=article['version']['repository_id'], status=article['version']['status'])
            db.session.add(a)
            db.session.flush()
            if 'comments' in article:
                restored_comments = []
                comment_signals.restore.send(comments=article['comments'], restored_comments=restored_comments)
                a.comments = restored_comments
                db.session.flush()
            if 'attachments' in article:
                def attachment_restored(attachment, attachment_name):
                    a.body = a.body.replace(attachment['file_path'], '/attachments/' + attachment_name)
                    db.session.flush()

                restored_attachments = []
                attachment_signals.restore.send(attachments=article['attachments'], directory=directory,
                                                restored_attachments=restored_attachments,
                                                attachment_restored=attachment_restored)
                a.attachments = restored_attachments
                db.session.flush()
            signals.restore.send(data=article, directory=directory, article=a)


@comment_signals.get_comment_show_info.connect
def get_comment_show_info(sender, comment, anchor, info, **kwargs):
    if comment.article is not None:
        info['title'] = comment.article.title
        info['url'] = url_for('main.show_article', slug=comment.article.slug, _anchor=anchor)


@signals.article_list_url.connect
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
        def get_articles(repository_id):
            return Article.query.filter_by(repository_id=repository_id).order_by(Article.version_timestamp.desc()).all()

        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        query = Article.query
        query = query.filter(Article.title.contains(search))
        query = query.group_by(Article.repository_id).order_by(Article.version_timestamp.desc())
        query_wrap = {'query': query}
        signals.custom_list.send(request=request, query_wrap=query_wrap)
        query = query_wrap['query']
        pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        articles = pagination.items
        pagination = db.session.query(Article.repository_id).group_by(Article.repository_id).order_by(
            Article.version_timestamp.desc()).paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'],
                                                       error_out=False)
        repository_ids = [item[0] for item in pagination.items]
        templates.append(render_template(article.template_path('list.html'), repository_ids=repository_ids,
                                         pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                                     'url_for': article_instance.url_for},
                                         get_articles=get_articles,
                                         url_for=article_instance.url_for))
        scripts.append(render_template(article.template_path('list.js.html')))


@article.route('admin', '/edit', '撰写文章')
def edit_article(request, templates, scripts, csss, **kwargs):
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        body = request.form['body']
        timestamp = datetime.utcfromtimestamp(int(request.form['timestamp']))
        article = Article.query.get(int(request.form['id']))
        if article.repository_id is None:
            repository_id = str(uuid4())
        else:
            repository_id = article.repository_id
        new_article = Article(title=title, slug=slug, body=body, timestamp=timestamp, author=article.author,
                              comments=article.comments, attachments=article.attachments, repository_id=repository_id,
                              status='published')
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            if slug == 'category':
                categories = []
                category_signals.set_widget.send(js_data=js_data, categories=categories)
                new_article.categories = categories
            if slug == 'tag':
                tags = []
                tag_signals.set_widget.send(js_data=js_data, tags=tags)
                new_article.tags = tags
        new_article.article_count = ArticleCount(view_count=article.article_count.view_count)
        db.session.add(new_article)
        db.session.commit()
    else:
        if 'id' in request.args:
            article = Article.query.get(int(request.args['id']))
        else:
            article = Article()
            db.session.add(article)
            db.session.commit()
        widgets = []
        # signals.show_edit_article_widget.send(request=request, article=article, widgets=widgets)
        widget = {'widget': None}
        attachment_signals.get_widget.send(attachments=article.attachments,
                                           meta={'type': 'article', 'article_id': article.id}, widget=widget)
        widgets.append(widget['widget'])
        category_signals.get_widget.send(categories=article.categories, widget=widget)
        widgets.append(widget['widget'])
        tag_signals.get_widget.send(tags=article.tags, widget=widget)
        widgets.append(widget['widget'])
        templates.append(
            render_template(article_instance.template_path('edit.html'), article=article, widgets=widgets))
        scripts.append(
            render_template(article_instance.template_path('edit.js.html'), article=article, widgets=widgets))
        csss.append(render_template(article_instance.template_path('edit.css.html'), widgets=widgets))


@comment_signals.on_new_comment.connect
def on_new_comment(sender, comment, meta, **kwargs):
    if 'type' in meta and meta['type'] == 'article':
        article_id = int(meta['article_id'])
        article = Article.query.get(article_id)
        article.comments.append(comment)
        db.session.commit()


@attachment_signals.on_new_attachment.connect
def on_new_attachment(sender, attachment, meta, **kwargs):
    if 'type' in meta and meta['type'] == 'article':
        article_id = int(meta['article_id'])
        article = Article.query.get(article_id)
        article.attachments.append(attachment)
        db.session.commit()
