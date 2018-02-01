from . import signals
from ...models import Post
from flask import current_app
import os.path


@signals.index.connect
def index(sender, args, context, contents, **kwargs):
    page = args.get('page', 1, type=int)
    pagination = Post.query_articles().order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    context['posts'] = posts
    context['pagination'] = pagination
    contents.append(os.path.join('article_list', 'templates', 'content.html'))
