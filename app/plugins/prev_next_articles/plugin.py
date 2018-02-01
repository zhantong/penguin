from . import signals
from ...models import Post
import os.path


@signals.article.connect
def article(sender, post, context, left_widgets, **kwargs):
    prev_next_articles = []
    prev_article = Post.query.filter(Post.timestamp < post.timestamp).order_by(Post.timestamp.desc()).limit(1).first()
    if prev_article is not None:
        prev_next_articles.append(prev_article)
    next_article = Post.query.filter(Post.timestamp > post.timestamp).order_by(Post.timestamp).limit(1).first()
    if next_article is not None:
        prev_next_articles.append(next_article)
    context['prev_next_articles'] = prev_next_articles
    left_widgets.append(os.path.join('prev_next_articles', 'templates', 'widget_content.html'))
