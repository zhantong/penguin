from . import signals
from ..post.models import Post, PostStatus
from ...main import main
from flask import render_template, request, make_response
import os.path
from ..post.signals import update_post, custom_list, edit_post, create_post, post_list_column_head, post_list_column, \
    post_search_select
from ...admin.signals import sidebar
from ...signals import restore
from datetime import datetime
from ...models import User
from ...models import db


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
    article_content = {'article_content': os.path.join('article', 'templates', 'article_content.html')}
    signals.article.send(args=args, cookies=cookies, post=post, context=context, article_content=article_content,
                         styles=styles, before_contents=before_contents, contents=contents, article_metas=article_metas,
                         left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts,
                         cookies_to_set=cookies_to_set)
    resp = make_response(render_template(os.path.join('article', 'templates', 'article.html'), **context, post=post,
                                         article_content=article_content['article_content'], styles=styles,
                                         before_contents=before_contents, contents=contents,
                                         article_metas=article_metas, left_widgets=left_widgets,
                                         right_widgets=right_widgets, scripts=scripts))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('article', 'templates', 'sidebar.html'))


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
            a = Post.create()
            a.update(title=article['title'], slug=article['slug'], post_type='article',
                     body=article['body'],
                     timestamp=datetime.utcfromtimestamp(article['timestamp']),
                     post_status=PostStatus.published(), author=User.query.filter_by(username=article['author']).one())
            db.session.add(a)
            db.session.flush()
            signals.restore_article.send(data=article, directory=directory, article=a)
