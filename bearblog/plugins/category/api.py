from flask import Response, request

from bearblog import component_route
from .models import Category
from bearblog.extensions import db


@component_route('/categories', 'categories', 'api')
def categories():
    all_category = Category.query.order_by(Category.name).all()
    return {'categories': [category.to_json() for category in all_category]}


@component_route('/admin/categories', 'get_categories', 'api')
def get_categories():
    return {
        'value': [category.to_json('admin_brief') for category in Category.query.all()]
    }


@component_route('/admin/category/<int:id>', 'delete_category', 'api', methods=['DELETE'])
def delete_category(id):
    category = Category.query.get(int(id))
    db.session.delete(category)
    db.session.commit()
    return Response(status=200)


@component_route('/admin/category/<int:id>', 'admin_category', 'api', methods=['GET'])
def admin_category(id):
    category = Category.query.get(int(id))
    return category.to_json(level='admin_full')


@component_route('/admin/category/<int:id>', 'update_category', 'api', methods=['PATCH'])
def update_category(id):
    data = request.get_json()
    category = Category.query.get(id)
    category.name = data['name']
    category.description = data['description']
    db.session.commit()

    return admin_category(id)
