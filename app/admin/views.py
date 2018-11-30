from flask import render_template, request, jsonify, abort
from flask_login import login_required
from . import admin
from ..utils import slugify
from ..plugins.models import Plugin


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    return render_template('admin/index.html', plugins=Plugin.plugins)


@admin.route('/<path:path>', methods=['GET', 'POST'])
def dispatch(path):
    plugin_slug = path.split('/')[0]
    templates = []
    scripts = []
    csss = []
    meta = {
        'override_render': False
    }
    Plugin.find_plugin(plugin_slug).request(path, request=request, templates=templates, scripts=scripts, csss=csss,
                                            meta=meta)
    if meta['override_render']:
        if len(templates) == 0:
            abort(404)
        else:
            return templates[0]
    return render_template('admin/framework.html', plugins=Plugin.plugins, templates=templates, scripts=scripts,
                           csss=csss)


@admin.route('/trans-slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
