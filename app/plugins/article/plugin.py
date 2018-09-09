from . import signals, meta
from ..post.models import Post, PostStatus
from ...main import main
from flask import render_template, request, make_response, redirect, url_for, current_app
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
from ..models import Plugin
from .models import Article, Status
from ..comment import signals as comment_signals

article = Plugin('文章', 'article')
article_instance = article


@main.route('/archives/')
def show_none_post():
    pass


@main.route('/archives/<string:slug>.html')
def show_article(slug):
    args = request.args
    cookies = request.cookies
    post = Post.query.filter_by(slug=slug).first_or_404()
    context = {}
    styles = []
    before_contents = []
    contents = []
    left_widgets = []
    right_widgets = []
    scripts = []
    cookies_to_set = {}
    article_metas = []
    article_content = {'article_content': Path('article', 'templates', 'article_content.html').as_posix()}
    signals.article.send(args=args, cookies=cookies, post=post, context=context, article_content=article_content,
                         styles=styles, before_contents=before_contents, contents=contents, article_metas=article_metas,
                         left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts,
                         cookies_to_set=cookies_to_set)
    resp = make_response(render_template(Path('article', 'templates', 'article.html').as_posix(), **context, post=post,
                                         article_content=article_content['article_content'], styles=styles,
                                         before_contents=before_contents, contents=contents,
                                         article_metas=article_metas, left_widgets=left_widgets,
                                         right_widgets=right_widgets, scripts=scripts))
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
                        timestamp=datetime.utcfromtimestamp(article['timestamp']), status=Status.published(),
                        author=User.query.filter_by(username=article['author']).one())
            db.session.add(a)
            db.session.flush()
            if 'comments' in article:
                restored_comments = []
                comment_signals.restore.send(comments=article['comments'], restored_comments=restored_comments)
                a.comments = restored_comments
                db.session.flush()
            signals.restore.send(data=article, directory=directory, article=a)


@comment_signals.get_comment_show_info.connect
def get_comment_show_info(sender, comment, anchor, info, **kwargs):
    if comment.article is not None:
        info['title'] = comment.article.title
        info['url'] = url_for('.show_article', slug=comment.article.slug, _anchor=anchor)


@signals.article_list_url.connect
def article_list_url(sender, params, **kwargs):
    return url_for('.dispatch', path=meta.PLUGIN_NAME + '/' + 'list', **params)


@article.route('admin', '/list', '管理文章')
def article_list(request, templates, **kwargs):
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    query = Post.query.filter(Post.post_type == 'article')
    query = query.filter(Post.title.contains(search))
    query = query.order_by(Post.timestamp.desc())
    query_wrap = {'query': query}
    signals.custom_list.send(request=request, query_wrap=query_wrap)
    query = query_wrap['query']
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    articles = pagination.items
    head = ['标题', '作者', '时间']
    signals.list_column_head.send(request=request, head=head)
    rows = []
    for article in articles:
        row = [Hyperlink('Hyperlink', article.title if article.title else '（无标题）',
                         url_for('.edit', type='post', id=article.id))
            , Plain('Plain', article.author.name)
            , Datetime('Datetime', article.timestamp)]
        signals.list_column.send(request=request, article=article, row=row)
        rows.append(row)
    templates.append(render_template(os.path.join('article', 'templates', 'list.html'), head=head, rows=rows,
                                     pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                                 'url_for': article_instance.url_for}))


@article.route('admin', '/edit', '撰写文章')
def edit_article(request, templates, scripts, csss, **kwargs):
    if 'id' in request.args:
        post = Post.query.get(int(request.args['id']))
    else:
        post = Post.create(request.args)
        db.session.add(post)
        db.session.commit()
    widgets = []
    signals.show_edit_article_widget.send(request=request, post=post, widgets=widgets)
    templates.append(render_template(os.path.join('article', 'templates', 'edit.html'), post=post, widgets=widgets))
    scripts.append(render_template(os.path.join('article', 'templates', 'edit.js.html'), post=post, widgets=widgets))
    csss.append(render_template(os.path.join('article', 'templates', 'edit.css.html'), widgets=widgets))
