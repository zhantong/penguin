from flask import Response, request

from bearblog import component_route
from .models import Tag
from bearblog.plugins import current_plugin
from bearblog.models import Signal
from bearblog.extensions import db

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/tags', 'get_tags', 'api_admin')
def get_tags():
    return {
        'value': [tag.to_json('admin_brief') for tag in Tag.query.all()]
    }


@component_route('/tag/<int:id>', 'delete_tag', 'api_admin', methods=['DELETE'])
def delete_tag(id):
    tag = Tag.query.get(int(id))
    db.session.delete(tag)
    db.session.commit()
    return Response(status=200)


@component_route('/tag/<int:id>', 'admin_tag', 'api_admin', methods=['GET'])
def admin_tag(id):
    tag = Tag.query.get(int(id))
    return tag.to_json(level='admin_full')


@component_route('/tag/<int:id>', 'update_tag', 'api_admin', methods=['PATCH'])
def update_tag(id):
    data = request.get_json()
    tag = Tag.query.get(id)
    tag.name = data['name']
    tag.description = data['description']
    db.session.commit()

    return admin_tag(id)
