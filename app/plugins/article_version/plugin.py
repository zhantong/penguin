from . import signals
from .models import ArticleVersion
from uuid import uuid4


@signals.on_new_article.connect
def on_new_article(sender, article, **kwargs):
    if article.article_version is None:
        article.article_version = ArticleVersion(repository_id=str(uuid4()), status='published', remark='init')
    else:
        article.article_version = ArticleVersion(repository_id=article.article_version.repository_id,
                                                 status='published')
