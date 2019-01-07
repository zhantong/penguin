from flask import render_template, request, jsonify, abort
from flask_login import login_required

from bearblog import current_component, component_route
from bearblog.models import Component
from bearblog.utils import slugify


@current_component.blueprint.before_request
@login_required
def before_request():
    pass


def get_sidebar_item(component):
    return current_component.signal.send_this('sidebar_item', component=component)


@component_route('/', 'index')
def index():
    return render_template('admin/index.html', components=Component._components, get_sidebar_item=get_sidebar_item)


@component_route('/<path:path>', 'all', methods=['GET', 'POST'])
def dispatch(path):
    templates = []
    scripts = []
    csss = []
    meta = {'override_render': False}
    component_slug = path.split('/')[0]
    path = path[len(component_slug + '/'):]
    Component.find_component(component_slug).request(path, request=request, templates=templates, scripts=scripts, csss=csss, meta=meta)
    if meta['override_render']:
        if len(templates) == 0:
            abort(404)
        else:
            return templates[0]
    return render_template('admin/framework.html', components=Component._components, get_sidebar_item=get_sidebar_item, templates=templates, scripts=scripts, csss=csss)


@component_route('/trans-slug', 'trans_slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
