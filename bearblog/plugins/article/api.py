from flask import request

from bearblog import component_route
from .models import Article
from bearblog.settings import get_setting
from .plugin import filter
from bearblog.plugins import current_plugin
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/articles', 'articles', 'api')
def articles():
    page = request.args.get('page', 1, type=int)
    query = Article.query_published().order_by(Article.timestamp.desc())
    query = {'query': query}
    filter(query, request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
    articles = pagination.items
    return {
        'articles': [article.to_json() for article in articles],
        'page': pagination.page,
        'next_page_num': pagination.next_num,
        'prev_page_num': pagination.per_page
    }


@component_route('/article/<int:number>', 'article', 'api')
def article(number):
    article = Article.query.filter_by(number=number).first_or_404()
    return article.to_json(level='full')


@component_route('/article/<int:number>/<path:path>', 'api_proxy', 'api', methods=['GET', 'POST'])
def api_proxy(number, path):
    article = Article.query.filter_by(number=number).first_or_404()
    widget = path.split('/')[0]
    return Signal.send('api_proxy', widget=widget, path=path, request=request, article=article)