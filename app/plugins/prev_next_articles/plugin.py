from ..post.models import Post
from ..article.signals import article
from ...plugins import add_template_file
from pathlib import Path


@article.connect
def article(sender, post, context, left_widgets, **kwargs):
    prev_next_articles = []
    prev_article = Post.query.filter(Post.timestamp < post.timestamp).order_by(Post.timestamp.desc()).limit(1).first()
    if prev_article is not None:
        prev_next_articles.append(prev_article)
    next_article = Post.query.filter(Post.timestamp > post.timestamp).order_by(Post.timestamp).limit(1).first()
    if next_article is not None:
        prev_next_articles.append(next_article)
    context['prev_next_articles'] = prev_next_articles
    add_template_file(left_widgets, Path(__file__), 'templates', 'widget_content.html')
