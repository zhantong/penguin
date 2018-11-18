from flask import url_for, render_template
from ...main import main
from pathlib import Path
from ..article.models import Article
from . import signals


@main.route('/list.html')
def article_contents():
    articles = Article.query_published().order_by(Article.timestamp.desc()).all()
    return render_template(Path('article_contents', 'templates', 'article_contents.html').as_posix(), articles=articles)


@signals.get_navbar_item.connect
def get_navbar_item(sender, item, **kwargs):
    item['item'] = {
        'type': 'item',
        'name': '文章目录',
        'link': url_for('main.article_contents')
    }
