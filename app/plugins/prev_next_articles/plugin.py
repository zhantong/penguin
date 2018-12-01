from ..article.models import Article
from flask import render_template
from ..models import Plugin

prev_next_articles = Plugin('上一篇/下一篇文章', 'prev_next_articles')
prev_next_articles_instance = prev_next_articles

prev_next_articles_instance.signal.declare_signal('get_widget', return_type='single')


@prev_next_articles_instance.signal.connect_this('get_widget')
def get_widget(sender, article, **kwargs):
    prev_next_articles = []
    prev_article = Article.query_published().filter(Article.timestamp < article.timestamp).order_by(
        Article.timestamp.desc()).limit(1).first()
    if prev_article is not None:
        prev_next_articles.append(prev_article)
    next_article = Article.query_published().filter(Article.timestamp > article.timestamp).order_by(
        Article.timestamp).limit(1).first()
    if next_article is not None:
        prev_next_articles.append(next_article)
    return {
        'slug': 'prev_next_articles',
        'name': '上一篇/下一篇文章',
        'html': render_template(prev_next_articles_instance.template_path('widget_content.html'),
                                prev_next_articles=prev_next_articles)
    }
