from . import signals
from ..post.models import Post
from ...main import main
from flask import render_template, url_for
import os.path
from ..post.signals import update_post, custom_list, edit_post, create_post
from ...signals import navbar
from ...admin.signals import sidebar


@main.route('/<string:slug>.html')
def show_page(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    context = {}
    contents = []
    scripts = []
    page_content = {'page_content': os.path.join('page', 'templates', 'page_content.html')}
    signals.page.send(post=post, context=context, page_content=page_content, contents=contents, scripts=scripts)
    return render_template(os.path.join('page', 'templates', 'page.html'), **context, post=post,
                           page_content=page_content['page_content'], contents=contents, scripts=scripts)


@navbar.connect
def navbar(sender, content):
    pages = Post.query.filter_by(post_type='page').all()
    content['items'].extend((page.title, url_for('main.show_page', slug=page.slug)) for page in pages)


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('page', 'templates', 'sidebar.html'))


@custom_list.connect
def custom_list(sender, args, query):
    if 'sub_type' in args and args['sub_type'] == 'page':
        query['query'] = query['query'].filter(Post.post_type == 'page')
    return query


@create_post.connect
def create_post(sender, post, args):
    if args is not None and 'sub_type' in args and args['sub_type'] == 'page':
        post.post_type = 'page'


@edit_post.connect
def edit_post(sender, post, args, context, styles, hiddens, contents, widgets, scripts):
    if post.post_type == 'page':
        signals.edit_page.send(args=args, context=context, styles=styles, hiddens=hiddens, contents=contents,
                               widgets=widgets,
                               scripts=scripts)


@update_post.connect
def update_post(sender, post, **kwargs):
    if post.post_type == 'page':
        if 'action' in kwargs:
            action = kwargs['action']
            if action in ['save-draft', 'publish']:
                signals.submit_page.send(form=kwargs['form'], post=post)
            else:
                signals.submit_page_with_action.send(kwargs['form']['action'], form=kwargs['form'], post=post)
