from blinker import signal
from ..post.models import Post, PostType
from ...main import main
from flask import render_template, url_for
import os.path

navbar = signal('navbar')
sidebar = signal('sidebar')
custom_list = signal('custom_list')
create_post = signal('create_post')
edit_post = signal('edit_post')
submit_post = signal('submit_post')
submit_post_with_action = signal('submit_post_with_action')
edit = signal('edit')
edit_page = signal('edit_page')
submit = signal('submit')
submit_page = signal('submit_page')
submit_page_with_action = signal('submit_page_with_action')
page = signal('page')


@main.route('/<string:slug>.html')
def show_page(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    context = {}
    contents = []
    scripts = []
    page_content = {'page_content': os.path.join('page', 'templates', 'page_content.html')}
    page.send(post=post, context=context, page_content=page_content, contents=contents, scripts=scripts)
    return render_template(os.path.join('page', 'templates', 'page.html'), **context, post=post,
                           page_content=page_content['page_content'], contents=contents, scripts=scripts)


@navbar.connect
def navbar(sender, content):
    pages = Post.query.filter_by(post_type=PostType.page()).all()
    content['items'].extend((page.title, url_for('main.show_page', slug=page.slug)) for page in pages)


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('page', 'templates', 'sidebar.html'))


@custom_list.connect
def custom_list(sender, args, query):
    if 'sub_type' in args and args['sub_type'] == 'page':
        query['query'] = query['query'].filter(Post.post_type == PostType.page())
    return query


@create_post.connect
def create_post(sender, args):
    if 'sub_type' in args and args['sub_type'] == 'page':
        return Post.create_page()


@edit_post.connect
def edit_post(sender, post, args, context, styles, hiddens, contents, widgets, scripts):
    if post.post_type == PostType.page():
        edit_page.send(args=args, context=context, styles=styles, hiddens=hiddens,
                       contents=contents, widgets=widgets,
                       scripts=scripts)


@submit_post.connect
def submit_post(sender, form, post):
    if post.post_type == PostType.page():
        submit_post.send(form=form, post=post)


@submit_post_with_action.connect
def submit_post_with_action(sender, form, post):
    if post.post_type == PostType.page():
        submit_post_with_action.send(form=form, post=post)
