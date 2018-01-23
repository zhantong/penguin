from blinker import signal
from ...models import db, Comment
from flask import current_app, url_for, flash
from ...element_models import Hyperlink, Table, Pagination, Plain, Datetime
from sqlalchemy import desc

show_list = signal('show_list')
manage = signal('manage')


@show_list.connect_via('comment')
def show_list(sender, args):
    page = args.get('page', 1, type=int)
    pagination = Comment.query.order_by(desc(Comment.timestamp)) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    comments = pagination.items
    head = ('', '标题', '作者', '时间', '内容')
    rows = []
    for comment in comments:
        rows.append((comment.id
                     , Hyperlink('Hyperlink', comment.post.title,
                                 url_for('main.show_post', slug=comment.post.slug,
                                         _anchor='comment-' + str(comment.id)))
                     , Plain('Plain', comment.author.name)
                     , Datetime('Datetime', comment.timestamp)
                     , Plain('Plain', comment.body_html)))
    table = Table('Table', head, rows)
    args = args.to_dict()
    if 'page' in args:
        del args['page']
    return {
        **args,
        'title': '评论',
        'table': table,
        'disable_search': True,
        'pagination': Pagination('Pagination', pagination, 'admin.show_list', args)
    }


@manage.connect_via('comment')
def manage(sender, form):
    action = form.get('action', '', type=str)
    if action == 'delete':
        ids = form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_comment_name = Comment.query.get(ids[0]).body
            for comment in Comment.query.filter(Comment.id.in_(ids)):
                db.session.delete(comment)
            db.session.commit()
            message = '已删除分类"' + first_comment_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '条评论'
            flash(message)
