from flask import render_template, request, current_app
from flask_login import login_required
from . import admin
from ..models import Post


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/write-post')
def write_post():
    return render_template('admin/write-post.html')


@admin.route('/manage-posts')
def manage_posts():
    action = request.args.get('action', 'list', type=str)
    if action == 'list':
        page = request.args.get('page', 1, type=int)
        keyword = request.args.get('keyword', '', type=str)
        pagination = Post.query.filter(Post.title.contains(keyword)).order_by(Post.timestamp.desc()).paginate(
            page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        posts = pagination.items
        return render_template('admin/manage-posts.html', posts=posts, pagination=pagination, keyword=keyword)
