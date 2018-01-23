from blinker import signal
from ...models import db, Post, PostStatus
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Datetime, Table, Tabs, Pagination

show_list = signal('show_list')
manage = signal('manage')


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
                                 url_for('admin.edit_article', id=post.id))
                     , Plain('Plain', post.author.name)
                     , Datetime('Datetime', post.timestamp)))
    tabs = Tabs('Tabs', [Hyperlink('Hyperlink', '全部', url_for('.list_articles', tab='全部'))], selected_tab=selected_tab)
    tabs.tabs.extend(list(
        Hyperlink('Hyperlink', post_status.name, url_for('.list_articles', tab=post_status.name)) for post_status in
        PostStatus.query.all()))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '文章',
        'tabs': tabs,
        'table': table,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
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
