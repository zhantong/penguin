from flask import render_template, request, jsonify
from flask_login import login_required

from bearblog import current_component, component_route
from bearblog.models import Component, Signal
from bearblog.utils import slugify

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@login_required
@current_component.blueprint.before_request
def before_request():
    pass


@current_component.blueprint.after_request
def after_request(response):
    response.set_data(render_template('admin/framework.html', components=Component._components, sidebar_items=get_sidebar_item(), content=response.get_data().decode()))
    return response


def get_sidebar_item():
    return Signal.send('sidebar_item')


@component_route('/', 'index')
def index():
    return ''


@component_route('/trans-slug', 'trans_slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
