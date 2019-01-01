from flask import render_template, request, jsonify, abort
from flask_login import login_required
from . import admin
from ..utils import slugify
from ..models import Component

current_component = Component.current_component()


@admin.before_request
@login_required
def before_request():
    pass


def get_sidebar_item(component):
    return current_component.signal.send_this('sidebar_item', component=component)


@admin.route('/')
def index():
    return render_template('admin/index.html', components=Component._components, get_sidebar_item=get_sidebar_item)


@admin.route('/<path:path>', methods=['GET', 'POST'])
def dispatch(path):
    templates = []
    scripts = []
    csss = []
    meta = {'override_render': False}
    current_component.signal.send_this('request', path=path, request=request, templates=templates, scripts=scripts, csss=csss, meta=meta)
    if meta['override_render']:
        if len(templates) == 0:
            abort(404)
        else:
            return templates[0]
    return render_template('admin/framework.html', components=Component._components, get_sidebar_item=get_sidebar_item, templates=templates, scripts=scripts, csss=csss)


@admin.route('/trans-slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
