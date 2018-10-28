from . import signals
from flask import current_app, render_template
from ...main.signals import index
from ..article.models import Article
from ..models import Plugin

article_list = Plugin('文章列表', 'article_list')


@index.connect
def index(sender, request, contents, **kwargs):
    page = request.args.get('page', 1, type=int)
    query = {
        'query': Article.query_published().order_by(Article.timestamp.desc())
    }
    signals.custom_article_list.send(request=request, query=query)
    pagination = query['query'].paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    articles = pagination.items
    contents.append(render_template(article_list.template_path('content.html'), articles=articles,
                                    pagination=pagination))
