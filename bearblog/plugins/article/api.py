from flask import request, Response
import dateutil.parser
from uuid import uuid4
from sqlalchemy import func
from flask_jwt_extended import get_jwt_identity

from bearblog import component_route
from .models import Article
from bearblog.settings import get_setting
from .plugin import filter
from bearblog.plugins import current_plugin
from bearblog.models import Signal, User
from bearblog.extensions import db

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


@component_route('/article/<int:number>', 'article', 'api', methods=['GET'])
def article(number):
    article = Article.query.filter_by(number=number).first_or_404()
    return article.to_json(level='full')


@component_route('/article/<int:id>', 'admin_article', 'api_admin', methods=['GET'])
def admin_article(id):
    article = Article.query.get(int(id))
    json_article = article.to_json(level='admin_full')
    json_article['plugin'] = Signal.send('get_admin_article', article=article)
    return json_article


@component_route('/article/<int:id>', 'update_article', 'api_admin', methods=['PATCH'])
def update_article(id):
    data = request.get_json()
    title = data['title']
    body = data['body']
    timestamp = dateutil.parser.parse(data['timestamp'])
    article = Article.query.get(int(id))
    if article.repository_id is None:
        repository_id = str(uuid4())
    else:
        repository_id = article.repository_id
    new_article = Article(title=title, body=body, timestamp=timestamp, author=article.author, repository_id=repository_id, status='published')
    Signal.send('duplicate', old_article=article, new_article=new_article)
    Signal.send('update_article', article=new_article, data=data['plugin'])
    db.session.add(new_article)
    db.session.commit()
    return admin_article(new_article.id)


@component_route('/article/<int:id>', 'delete_article', 'api_admin', methods=['DELETE'])
def delete_article(id):
    article = Article.query.get(int(id))
    db.session.delete(article)
    db.session.commit()
    return Response(status=200)


@component_route('/article/<int:number>/<path:path>', 'api_proxy', 'api', methods=['GET', 'POST'])
def api_proxy(number, path):
    article = Article.query.filter_by(number=number).first_or_404()
    widget = path.split('/')[0]
    return Signal.send('api_proxy', widget=widget, path=path, request=request, article=article)


@component_route('/article/<int:id>/<path:path>', 'admin_api_proxy', 'api_admin', methods=['GET', 'POST', 'DELETE'])
def admin_api_proxy(id, path):
    article = Article.query.get(id)
    widget = path.split('/')[0]
    return Signal.send('admin_api_proxy', widget=widget, path=path, request=request, article=article)


@component_route('/articles', 'admin_articles', 'api_admin')
def admin_articles():
    def get_articles(repository_id):
        return Article.query.filter_by(repository_id=repository_id).order_by(Article.version_timestamp.desc()).all()

    page = request.args.get('page', 1, type=int)
    query = db.session.query(Article.repository_id).order_by(func.max(Article.version_timestamp).desc()).group_by(Article.repository_id)
    query = {'query': query}
    filter(query, request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    return {
        'value': [{'repositoryId': repository_id, 'articles': [article.to_json('admin_brief') for article in get_articles(repository_id)]} for repository_id in repository_ids]
    }


@component_route('/articles', 'create_article', 'api_admin', methods=['POST'])
def create_article():
    data = request.get_json()
    title = data['title']
    body = data['body']
    timestamp = dateutil.parser.parse(data['timestamp'])
    current_username = get_jwt_identity()
    user = User.query.filter_by(username=current_username).first()
    new_article = Article(title=title, body=body, timestamp=timestamp, author=user, repository_id=str(uuid4()), status='published')
    Signal.send('update_article', article=new_article, data=data['plugin'])
    db.session.add(new_article)
    db.session.commit()
    return admin_article(new_article.id)
