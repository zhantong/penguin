from blinker import signal
from ...models import Post, PostType
import os.path

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
