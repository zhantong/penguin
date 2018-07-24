from flask import url_for, render_template
from ...main import main
from ..post.models import Post
from ...signals import navbar
from . import signals
from pathlib import Path


@main.route('/list.html')
def article_contents():
    articles = Post.query_articles().order_by(Post.timestamp.desc()).all()
    column_heads = []
    columns = []
    signals.article_contents_column_head.send(column_heads=column_heads)
    signals.article_contents_column.send(columns=columns)
    return render_template(Path('article_contents', 'templates', 'article_contents.html').as_posix(), articles=articles,
                           column_heads=column_heads, columns=columns)


@navbar.connect
def navbar(sender, content):
    content['items'].append(('文章目录', url_for('main.article_contents')))
