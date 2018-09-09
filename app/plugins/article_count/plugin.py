from ..article.signals import article
from .models import ArticleCount
from ...models import db
import json
from ..article_contents.signals import article_contents_column_head, article_contents_column
from ..article_list.signals import article_list_meta
from ...plugins import add_template_file
from pathlib import Path
from ..article import signals as article_signals


@article.connect
def article(sender, post, context, article_metas, cookies, cookies_to_set, **kwargs):
    article_count_viewed_articles = cookies.get('article_count_viewed_articles')
    if article_count_viewed_articles is None:
        article_count_viewed_articles = []
    else:
        article_count_viewed_articles = json.loads(article_count_viewed_articles)
    if post.id not in article_count_viewed_articles:
        post.article_count.view_count += 1
        db.session.commit()
        article_count_viewed_articles.append(post.id)
        cookies_to_set['article_count_viewed_articles'] = json.dumps(article_count_viewed_articles)
    context['view_count'] = post.article_count.view_count
    add_template_file(article_metas, Path(__file__), 'templates', 'main', 'article_meta.html')


@article_signals.restore.connect
def article_restore(sender, data, article, **kwargs):
    if 'article_counts' in data:
        ac = ArticleCount(article=article, view_count=data['article_counts']['view_count'])
        db.session.add(ac)
        db.session.flush()


@article_contents_column_head.connect
def article_contents_column_head(sender, column_heads, **kwargs):
    add_template_file(column_heads, Path(__file__), 'templates', 'main', 'article_contents_column_head.html')


@article_contents_column.connect
def article_contents_column(sender, columns, **kwargs):
    add_template_file(columns, Path(__file__), 'templates', 'main', 'article_contents_column.html')
