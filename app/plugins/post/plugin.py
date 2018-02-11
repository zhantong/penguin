from blinker import signal
from ...models import db
from .models import Post, PostStatus
from flask import current_app, url_for, flash, send_from_directory
from ...element_models import Hyperlink, Plain, Datetime, Table, Tabs, Pagination
import os.path
from datetime import datetime
from .. import plugin

show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
post_list_column_head = signal('post_list_column_head')
post_list_column = signal('post_list_column')
post_search_select = signal('post_search_select')
create_post = signal('create_post')
edit_post = signal('edit_post')
submit_post = signal('submit_post')
submit_post_with_action = signal('submit_post_with_action')
edit = signal('edit')
submit = signal('submit')


@plugin.route('/post/static/<path:filename>')
def post_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@show_list.connect_via('post')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    search = args.get('search', '', type=str)
    selected_tab = args.get('tab', '全部', type=str)
    query = Post.query.filter(Post.title.contains(search))
    if selected_tab != '全部':
        query = query.filter(Post.post_status.has(key=selected_tab))
    query = query.order_by(Post.timestamp.desc())
    result = custom_list.send(args=args, query={'query': query})
    if result:
        query = result[0][1]['query']
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    head = ['', '标题', '作者', '时间']
    post_list_column_head.send(args=args, head=head)
    rows = []
    for post in posts:
        row = [post.id
            , Hyperlink('Hyperlink', post.title if post.title else '（无标题）',
                        url_for('.edit', type='post', id=post.id))
            , Plain('Plain', post.author.name)
            , Datetime('Datetime', post.timestamp)]
        post_list_column.send(args=args, post=post, row=row)
        rows.append(row)
    tabs = Tabs('Tabs', [Hyperlink('Hyperlink', '全部', url_for('.show_list', type='post', tab='全部'))],
                selected_tab=selected_tab)
    tabs.tabs.extend(list(
        Hyperlink('Hyperlink', post_status.name, url_for('.show_list', type='post', tab=post_status.key)) for
        post_status in PostStatus.query.all()))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    search_selects = []
    post_search_select.send(args=args, selects=search_selects)
    return {
        **args,
        'title': 'POST',
        'tabs': tabs,
        'search_selects': search_selects,
        'table': table,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
    }


@manage.connect_via('post')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_post_title = Post.query.get(ids[0]).title
            for post in Post.query.filter(Post.id.in_(ids)):
                db.session.delete(post)
            db.session.commit()
            message = '已删除POST《' + first_post_title + '》'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '篇POST'
            flash(message)


@edit.connect_via('post')
def edit(sender, args, context, styles, hiddens, contents, widgets, scripts):
    if 'id' in args:
        post = Post.query.get(int(args['id']))
    else:
        result = create_post.send(args=args)
        for item in result:
            if item[1] is not None:
                post = item[1]
        db.session.add(post)
        db.session.commit()
        db.session.refresh(post)
    context['post'] = post
    styles.append(os.path.join('post', 'templates', 'style_editor.html'))
    hiddens.append(os.path.join('post', 'templates', 'hidden_id.html'))
    contents.append(os.path.join('post', 'templates', 'content_title.html'))
    contents.append(os.path.join('post', 'templates', 'content_slug.html'))
    contents.append(os.path.join('post', 'templates', 'content_editor.html'))
    scripts.append(os.path.join('post', 'templates', 'script_slug.html'))
    scripts.append(os.path.join('post', 'templates', 'script_editor.html'))
    widgets.append(os.path.join('post', 'templates', 'widget_content_submit.html'))
    scripts.append(os.path.join('post', 'templates', 'widget_script_submit.html'))
    edit_post.send(post=post, args=args, context=context, styles=styles, hiddens=hiddens,
                   contents=contents, widgets=widgets,
                   scripts=scripts)


@submit.connect_via('post')
def submit(sender, form):
    action = form.get('action')
    id = form['id']
    post = Post.query.get(int(id))
    if action in ['save-draft', 'publish']:
        title = form['title']
        slug = form['slug']
        body = form['body']
        timestamp = form.get('timestamp', type=int)

        timestamp = datetime.utcfromtimestamp(timestamp)
        post.title = title
        post.slug = slug
        post.body = body
        post.timestamp = timestamp

        if action == 'save-draft':
            post.set_post_status_draft()
        elif action == 'publish':
            post.set_post_status_published()
        submit_post.send(form=form, post=post)

        db.session.commit()
    else:
        submit_post_with_action.send(action, form=form, post=post)
