from blinker import signal
from ...models import db, Post, PostStatus
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Plain, Datetime, Table, Tabs, Pagination
import os.path
from datetime import datetime

show_list = signal('show_list')
manage = signal('manage')
custom_list = signal('custom_list')
article_search_select = signal('article_search_select')
edit = signal('edit')
edit_article = signal('edit_article')
submit = signal('submit')
submit_article = signal('submit_article')
submit_article_with_action = signal('submit_article_with_action')


@show_list.connect_via('article')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    search = args.get('search', '', type=str)
    selected_tab = args.get('tab', '全部', type=str)
    query = Post.query_articles().filter(Post.title.contains(search))
    if selected_tab != '全部':
        query = query.filter(Post.post_status.has(key=selected_tab))
    query = query.order_by(Post.timestamp.desc())
    result = custom_list.send(args=args, query={'query': query})
    if result:
        query = result[0][1]['query']
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    head = ('', '标题', '作者', '分类', '标签', '时间')
    rows = []
    for post in posts:
        rows.append((post.id
                     , Hyperlink('Hyperlink', post.title if post.title else '（无标题）',
                                 url_for('admin.edit_article', id=post.id))
                     , Plain('Plain', post.author.name)
                     , [Hyperlink('Hyperlink', category_post_meta.meta.value,
                                  url_for('.list_articles', category=category_post_meta.meta.key)) for
                        category_post_meta in post.category_post_metas.all()]
                     , [Hyperlink('Hyperlink', tag_post_meta.meta.value,
                                  url_for('.list_articles', tag=tag_post_meta.meta.key)) for tag_post_meta in
                        post.tag_post_metas.all()]
                     , Datetime('Datetime', post.timestamp)))
    tabs = Tabs('Tabs', [Hyperlink('Hyperlink', '全部', url_for('.list_articles', tab='全部'))], selected_tab=selected_tab)
    tabs.tabs.extend(list(
        Hyperlink('Hyperlink', post_status.name, url_for('.list_articles', tab=post_status.name)) for post_status in
        PostStatus.query.all()))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    search_selects = []
    result = article_search_select.send()
    for item in result:
        search_selects.append(item[1])
    return {
        **args,
        'title': '文章',
        'tabs': tabs,
        'search_selects': search_selects,
        'table': table,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
    }


@manage.connect_via('article')
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
            message = '已删除文章《' + first_post_title + '》'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '篇文章'
            flash(message)


@edit.connect_via('article')
def edit(sender, args, context, styles, hiddens, contents, widgets, scripts):
    if 'id' in args:
        post = Post.query.get(int(args['id']))
    else:
        post = Post.create_article()
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
    edit_article.send(args=args, context=context, styles=styles, hiddens=hiddens,
                      contents=contents, widgets=widgets,
                      scripts=scripts)


@submit.connect_via('article')
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
        submit_article.send(form=form, post=post)

        db.session.commit()
    else:
        submit_article_with_action.send(action, form=form)
