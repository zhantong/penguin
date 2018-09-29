from . import signals
from ..post.models import Post
from flask import current_app, render_template
from ...main.signals import index
from ...plugins import add_template_file
from pathlib import Path
from ..article.models import Article
import os.path
from ..models import Plugin

article_list = Plugin('文章列表', 'article_list')


@index.connect
def index(sender, request, contents, **kwargs):
    page = request.args.get('page', 1, type=int)
    query = {
        'query': Article.query.order_by(Article.timestamp.desc())
    }
    signals.custom_article_list.send(request=request, query=query)
    pagination = query['query'].paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    articles = pagination.items
    contents.append(render_template(article_list.template_path('content.html'), articles=articles,
                                    pagination=pagination))
