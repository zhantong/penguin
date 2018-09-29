from ..post.models import Post
from ..article.signals import article
from ...plugins import add_template_file
from pathlib import Path
from ..article.models import Article
from flask import render_template
import os.path
from ..article import signals as article_signals

from ..models import Plugin

prev_next_article = Plugin('上一篇/下一篇文章', 'prev_next_article')
prev_next_article_instance = prev_next_article


@article_signals.show.connect
def article_show(sender, article, left_widgets, **kwargs):
    prev_next_articles = []
    prev_article = Article.query.filter(Article.timestamp < article.timestamp).order_by(Article.timestamp.desc()).limit(
        1).first()
    if prev_article is not None:
        prev_next_articles.append(prev_article)
    next_article = Article.query.filter(Article.timestamp > article.timestamp).order_by(Article.timestamp).limit(
        1).first()
    if next_article is not None:
        prev_next_articles.append(next_article)
    left_widgets.append(
        render_template(prev_next_article.template_path('widget_content.html'), article=article,
                        prev_next_articles=prev_next_articles))
