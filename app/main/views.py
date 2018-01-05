from flask import render_template
from . import main
from ..models import Post


@main.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc())
    return render_template('index.html', posts=posts)
