from ..models import Plugin

article = Plugin('文章', 'article')
article_instance = article

from . import signals, meta
from ..post.models import Post, PostStatus
from ...main import main
from flask import render_template, request, make_response, redirect, url_for, current_app, session, flash, jsonify
from ..post.signals import update_post, custom_list, edit_post, create_post, post_list_column_head, post_list_column, \
    post_search_select
from ...admin.signals import sidebar
from ...signals import restore
from datetime import datetime
from ...models import User
from ...models import db
from ...plugins import add_template_file
from pathlib import Path
import os.path
from ...element_models import Hyperlink, Plain, Datetime

from .models import Article
from ..article_version.models import ArticleVersion
from ..comment import signals as comment_signals
from ..attachment import signals as attachment_signals
from ..category import signals as category_signals
from ..tag import signals as tag_signals
import json


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
    slug = Post.query.filter_by(number=number).first_or_404().slug
    return redirect(url_for('.show_article', slug=slug))


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@custom_list.connect
def custom_list(sender, args, query):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        query['query'] = query['query'].filter(Post.post_type == 'article')
    return query


@post_list_column_head.connect
def post_list_column_head(sender, args, head):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        signals.article_list_column_head.send(head=head)


@post_list_column.connect
def post_list_column(sender, args, post, row):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        signals.article_list_column.send(post=post, row=row)


@post_search_select.connect
def post_search_select(sender, args, selects):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        signals.article_search_select.send(selects=selects)


@create_post.connect
def create_post(sender, post, args):
    if args is not None and 'sub_type' in args and args['sub_type'] == 'article':
        post.post_type = 'article'


@edit_post.connect
def edit_post(sender, post, args, context, styles, hiddens, contents, widgets, scripts):
    if post.post_type == 'article':
        signals.edit_article.send(args=args, context=context, styles=styles, hiddens=hiddens, contents=contents,
                                  widgets=widgets, scripts=scripts)


@update_post.connect
def update_post(sender, post, **kwargs):
    if post.post_type == 'article':
        if 'action' in kwargs:
            action = kwargs['action']
            if action in ['save-draft', 'publish']:
                signals.submit_article.send(form=kwargs['form'], post=post)
            else:
                signals.submit_article_with_action.send(kwargs['form']['action'], form=kwargs['form'], post=post)


@restore.connect
def restore(sender, data, directory, **kwargs):
    if 'article' in data:
        articles = data['article']
        for article in articles:
            a = Article(title=article['title'], slug=article['slug'], body=article['body'],
                        timestamp=datetime.utcfromtimestamp(article['timestamp']),
                        author=User.query.filter_by(username=article['author']).one())
            db.session.add(a)
            db.session.flush()
            va = ArticleVersion(repository_id=article['version']['repository_id'], status=article['version']['status'],
                                article=a)
            db.session.add(va)
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
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        query = Article.query
        query = query.filter(Article.title.contains(search))
        query = query.order_by(Article.timestamp.desc())
        query_wrap = {'query': query}
        signals.custom_list.send(request=request, query_wrap=query_wrap)
        query = query_wrap['query']
        pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        articles = pagination.items
        templates.append(render_template(article.template_path('list.html'), articles=articles,
                                         pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                                     'url_for': article_instance.url_for},
                                         url_for=article_instance.url_for))
        scripts.append(render_template(article.template_path('list.js.html')))


@article.route('admin', '/edit', '撰写文章')
def edit_article(request, templates, scripts, csss, **kwargs):
    if request.method == 'POST':
        article = Article.query.get(int(request.form['id']))
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            if slug == 'category':
                categories = []
                category_signals.set_widget.send(js_data=js_data, categories=categories)
                article.categories = categories
            if slug == 'tag':
                tags = []
                tag_signals.set_widget.send(js_data=js_data, tags=tags)
                article.tags = tags
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
