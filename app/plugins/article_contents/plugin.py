from flask import url_for, render_template
from ...main import main
from ..post.models import Post
from ...signals import navbar
from . import signals
from pathlib import Path
from ..article.models import Article


@main.route('/list.html')
def article_contents():
    articles = Article.query.order_by(Article.timestamp.desc()).all()
    return render_template(Path('article_contents', 'templates', 'article_contents.html').as_posix(), articles=articles)


@navbar.connect
def navbar(sender, content):
    content['items'].append(('文章目录', url_for('main.article_contents')))
