from flask import request, Response
from sqlalchemy import func
import dateutil
from uuid import uuid4

from bearblog import component_route
from .models import Page
from bearblog.models import Signal
from bearblog.plugins import current_plugin
from bearblog.extensions import db
from bearblog.settings import get_setting

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/page/<string:slug>', 'page', 'api')
def page(slug):
    page = Page.query.filter_by(slug=slug).order_by(Page.version_timestamp.desc())
    if 'version' in request.args:
        page = page.filter_by(number=request.args['version'])
    page = page.first()
    return page.to_json(level='full')


@component_route('/pages', 'pages', 'api')
def pages():
    pages = Page.query.all()
    more = []
    for page in pages:
        more.append({
            'title': page.title,
            'slug': page.slug
        })
    dynamic_pages = Signal.send('dynamic_page')
    for page in dynamic_pages:
        more.append({
            'title': page['title'],
            'slug': page['slug']
        })
    return {'pages': more}


@component_route('/admin/pages', 'admin_pages', 'api')
def admin_pages():
    def get_pages(repository_id):
        return Page.query.filter_by(repository_id=repository_id).order_by(Page.version_timestamp.desc()).all()

    page = request.args.get('page', 1, type=int)
    query = db.session.query(Page.repository_id).order_by(func.max(Page.version_timestamp).desc()).group_by(Page.repository_id)
    query = {'query': query}
    filter(query, request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=get_setting('items_per_page').value, error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    return {
        'value': [{'repositoryId': repository_id, 'pages': [page.to_json('admin_brief') for page in get_pages(repository_id)]} for repository_id in repository_ids]
    }


@component_route('/admin/page/<int:id>', 'delete_page', 'api', methods=['DELETE'])
def delete_page(id):
    page = Page.query.get(int(id))
    db.session.delete(page)
    db.session.commit()
    return Response(status=200)


@component_route('/admin/page/<int:id>', 'admin_page', 'api', methods=['GET'])
def admin_page(id):
    page = Page.query.get(int(id))
    json_page = page.to_json(level='admin_full')
    return json_page


@component_route('/admin/page/<int:id>', 'update_page', 'api', methods=['PATCH'])
def update_page(id):
    data = request.get_json()
    title = data['title']
    body = data['body']
    timestamp = dateutil.parser.parse(data['timestamp'])
    page = Page.query.get(int(id))
    if page.repository_id is None:
        repository_id = str(uuid4())
    else:
        repository_id = page.repository_id
    new_page = Page(title=title, body=body, timestamp=timestamp, author=page.author, repository_id=repository_id, status='published')
    Signal.send('duplicate', old_page=page, new_page=new_page)
    Signal.send('update_page', page=new_page, data=data['plugin'])
    db.session.add(new_page)
    db.session.commit()
    return admin_page(new_page.id)
