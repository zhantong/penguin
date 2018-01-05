from flask import render_template
from . import main
from ..models import Post


@main.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc())
    return render_template('index.html', posts=posts)


@main.route('/archives/<slug>.html')
def show_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    return render_template('post.html', post=post)
