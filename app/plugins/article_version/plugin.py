from . import signals
from .models import ArticleVersion
from uuid import uuid4


@signals.on_new_article.connect
def on_new_article(sender, new_article, old_count, **kwargs):
    if new_article.article_version is None:
        new_article.article_version = ArticleVersion(repository_id=str(uuid4()), status='published', remark='init')
    else:
        new_article.article_version = ArticleVersion(repository_id=old_count.article_version.repository_id,
                                                     status='published')
