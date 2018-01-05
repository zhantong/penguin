from flask import render_template, request, current_app
from . import main
from ..models import Post, Comment
from ..utils import format_comments


@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('index.html', posts=posts, pagination=pagination)


@main.route('/archives/<slug>.html')
def show_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.desc()).all()
    comments = format_comments(comments)
    return render_template('post.html', post=post, comments=comments)
