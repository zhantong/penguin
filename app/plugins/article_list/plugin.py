from . import signals
from ..post.models import Post
from flask import current_app
from ...main.signals import index
from ...plugins import add_template_file
from pathlib import Path
from ..article.models import Article


@index.connect
def index(sender, args, context, contents, **kwargs):
    page = args.get('page', 1, type=int)
    query = {
        'query': Article.query.order_by(Article.timestamp.desc())
    }
    signals.custom_article_list.send(args=args, query=query)
    pagination = query['query'].paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    context['posts'] = posts
    context['pagination'] = pagination
    metas = []
    signals.article_list_meta.send(metas=metas)
    context['metas'] = metas
    add_template_file(contents, Path(__file__), 'templates', 'content.html')
