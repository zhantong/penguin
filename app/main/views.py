from flask import render_template
from . import main
from ..models import Post, Comment
from ..utils import format_comments


@main.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc())
    return render_template('index.html', posts=posts)


@main.route('/archives/<slug>.html')
def show_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.desc()).all()
    comments = format_comments(comments)
    return render_template('post.html', post=post, comments=comments)
