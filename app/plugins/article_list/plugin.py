from . import signals
from ..post.models import Post
from flask import current_app
import os.path
from ...main.signals import index


@index.connect
def index(sender, args, context, contents, **kwargs):
    page = args.get('page', 1, type=int)
    query = {
        'query': Post.query_articles().order_by(Post.timestamp.desc())
    }
    signals.custom_article_list.send(args=args, query=query)
    pagination = query['query'].paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    context['posts'] = posts
    context['pagination'] = pagination
    contents.append(os.path.join('article_list', 'templates', 'content.html'))
