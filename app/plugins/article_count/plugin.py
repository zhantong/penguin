from ..article.signals import article, restore_article
from .models import ArticleCount
from ...models import db
import os


@article.connect
def article(sender, post, context, article_metas, **kwargs):
    context['view_count'] = post.article_count.view_count
    article_metas.append(os.path.join('article_count', 'templates', 'main', 'article_meta.html'))


@restore_article.connect
def restore_article(sender, data, article, **kwargs):
    if 'article_counts' in data:
        ac = ArticleCount.create(post=article, view_count=data['article_counts']['view_count'])
        db.session.add(ac)
        db.session.flush()
