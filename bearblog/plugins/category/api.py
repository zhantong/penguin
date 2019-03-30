from bearblog import component_route
from .models import Category


@component_route('/categories', 'categories', 'api')
def categories():
    all_category = Category.query.order_by(Category.name).all()
    return {'categories': [category.to_json() for category in all_category]}


@component_route('/admin/categories', 'get_categories', 'api')
def get_categories():
    return {
        'value': [{'id': category.id, 'name': category.name} for category in Category.query.all()]
    }
