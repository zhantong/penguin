from blinker import signal
from ...models import db, Post, PostStatus
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Datetime, Table, Tabs, Pagination
import os.path
from datetime import datetime

sidebar = signal('sidebar')
show_list = signal('show_list')
manage = signal('manage')
edit = signal('edit')
edit_page = signal('edit_page')
submit = signal('submit')
submit_page = signal('submit_page')
submit_page_with_action = signal('submit_page_with_action')


@sidebar.connect
def sidebar(sender, sidebars):
    sidebars.append(os.path.join('page', 'templates', 'sidebar.html'))


@show_list.connect_via('page')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    search = args.get('search', '', type=str)
    selected_tab = args.get('tab', '全部', type=str)
    query = Post.query_pages().filter(Post.title.contains(search))
    if selected_tab != '全部':
        query = query.filter(Post.post_status.has(key=selected_tab))
    query = query.order_by(Post.timestamp.desc())
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    head = ('', '标题', '作者', '时间')
    rows = []
    for post in posts:
        rows.append((post.id
                     , Hyperlink('Hyperlink', post.title if post.title else '（无标题）',
                                 url_for('.edit', type='page', id=post.id))
                     , Plain('Plain', post.author.name)
                     , Datetime('Datetime', post.timestamp)))
    tabs = Tabs('Tabs', [Hyperlink('Hyperlink', '全部', url_for('.show_list', type='article', tab='全部'))],
                selected_tab=selected_tab)
    tabs.tabs.extend(list(
        Hyperlink('Hyperlink', post_status.name, url_for('.show_list', type='article', tab=post_status.name)) for
        post_status in
        PostStatus.query.all()))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '页面',
        'tabs': tabs,
        'table': table,
        'pagination': Pagination('Pagination', pagination, '.show_list', args)
    }


@manage.connect_via('page')
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
            message = '已删除页面《' + first_post_title + '》'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个页面'
            flash(message)


@edit.connect_via('page')
def edit(sender, args, context, styles, hiddens, contents, widgets, scripts):
    if 'id' in args:
        post = Post.query.get(int(args['id']))
    else:
        post = Post.create_page()
        db.session.add(post)
        db.session.commit()
        db.session.refresh(post)
    context['post'] = post
    styles.append(os.path.join('article', 'templates', 'style_editor.html'))
    hiddens.append(os.path.join('article', 'templates', 'hidden_id.html'))
    contents.append(os.path.join('article', 'templates', 'content_title.html'))
    contents.append(os.path.join('article', 'templates', 'content_slug.html'))
    contents.append(os.path.join('article', 'templates', 'content_editor.html'))
    scripts.append(os.path.join('article', 'templates', 'script_slug.html'))
    scripts.append(os.path.join('article', 'templates', 'script_editor.html'))
    widgets.append(os.path.join('article', 'templates', 'widget_content_submit.html'))
    scripts.append(os.path.join('article', 'templates', 'widget_script_submit.html'))
    edit_page.send(args=args, context=context, styles=styles, hiddens=hiddens,
                   contents=contents, widgets=widgets,
                   scripts=scripts)


@submit.connect_via('page')
def submit(sender, form):
    action = form.get('action')
    if action in ['save-draft', 'publish']:
        id = form['id']
        title = form['title']
        slug = form['slug']
        body = form['body']
        timestamp = form.get('timestamp', type=int)

        timestamp = datetime.utcfromtimestamp(timestamp)
        post = Post.query.get(int(id))
        post.title = title
        post.slug = slug
        post.body = body
        post.timestamp = timestamp

        if action == 'save-draft':
            post.set_post_status_draft()
        elif action == 'publish':
            post.set_post_status_published()
        submit_page.send(form=form, post=post)

        db.session.commit()
    else:
        submit_page_with_action.send(action, form=form)
