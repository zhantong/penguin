from blinker import signal
from ..post.models import Post
from ...main import main
from flask import render_template, request, flash
import os.path
from ..post.signals import update_post

navbar = signal('navbar')
sidebar = signal('sidebar')
custom_list = signal('custom_list')
post_list_column_head = signal('post_list_column_head')
post_list_column = signal('post_list_column')
post_search_select = signal('post_search_select')
create_post = signal('create_post')
edit_post = signal('edit_post')
article_list_column_head = signal('article_list_column_head')
article_list_column = signal('article_list_column')
article_search_select = signal('article_search_select')
edit = signal('edit')
edit_article = signal('edit_article')
submit = signal('submit')
submit_article = signal('submit_article')
submit_article_with_action = signal('submit_article_with_action')
article = signal('article')


@main.route('/archives/')
def show_none_post():
    pass


@main.route('/archives/<string:slug>.html')
def show_article(slug):
    args = request.args
    post = Post.query.filter_by(slug=slug).first_or_404()
    context = {}
    styles = []
    before_contents = []
    contents = []
    left_widgets = []
    right_widgets = []
    scripts = []
    flash('test')
    article_content = {'article_content': os.path.join('article', 'templates', 'article_content.html')}
    article.send(args=args, post=post, context=context, article_content=article_content, styles=styles,
                 before_contents=before_contents, contents=contents,
                 left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts)
    return render_template(os.path.join('article', 'templates', 'article.html'), **context, post=post,
                           article_content=article_content['article_content'], styles=styles,
                           before_contents=before_contents, contents=contents,
                           left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts)


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
        article_list_column_head.send(head=head)


@post_list_column.connect
def post_list_column(sender, args, post, row):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        article_list_column.send(post=post, row=row)


@post_search_select.connect
def post_search_select(sender, args, selects):
    if 'sub_type' not in args or args['sub_type'] == 'article':
        article_search_select.send(selects=selects)


@create_post.connect
def create_post(sender, post, args):
    if args is not None and 'sub_type' in args and args['sub_type'] == 'article':
        post.post_type = 'article'


@edit_post.connect
def edit_post(sender, post, args, context, styles, hiddens, contents, widgets, scripts):
    if post.post_type == 'article':
        edit_article.send(args=args, context=context, styles=styles, hiddens=hiddens, contents=contents,
                          widgets=widgets, scripts=scripts)


@update_post.connect
def update_post(sender, post, **kwargs):
    if post.post_type == 'article':
        if 'action' in kwargs:
            action = kwargs['action']
            if action in ['save-draft', 'publish']:
                submit_article.send(form=kwargs['form'], post=post)
            else:
                submit_article_with_action.send(kwargs['form']['action'], form=kwargs['form'], post=post)
