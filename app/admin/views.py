from . import signals
from flask import render_template, request, redirect, url_for, jsonify, abort
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
    sidebars = []
    signals.sidebar.send(sidebars=sidebars)
    return render_template('admin/index.html', sidebars=sidebars, plugins=Plugin.plugins)


@admin.route('/edit')
def edit():
    type = request.args['type']
    context = {}
    styles = []
    hiddens = []
    contents = []
    widgets = []
    scripts = []
    result = signals.edit.send(type, args=request.args, context=context, styles=styles, hiddens=hiddens,
                               contents=contents, widgets=widgets,
                               scripts=scripts)
    sidebars = []
    signals.sidebar.send(sidebars=sidebars)
    return render_template('admin/edit.html', **request.args.to_dict(), **context, sidebars=sidebars, styles=styles,
                           hiddens=hiddens,
                           contents=contents, widgets=widgets,
                           scripts=scripts, plugins=Plugin.plugins, templates=[])


@admin.route('/edit', methods=['POST'])
def submit():
    args = request.args
    type = request.form['type']
    result = signals.submit.send(type, args=args, form=request.form)
    return redirect(url_for('.show_list', type=type))


@admin.route('/manage')
def show_list():
    type = request.args['type']
    result = signals.show_list.send(type, args=request.args)
    if len(result) == 0:
        return redirect(url_for('.edit', type=type))
    context = result[0][1]
    sidebars = []
    signals.sidebar.send(sidebars=sidebars)
    return render_template('admin/manage.html', **context, sidebars=sidebars, plugins=Plugin.plugins, templates=[],
                           scripts=[], csss=[])


@admin.route('/manage', methods=['POST'])
def manage():
    type = request.form['type']
    result = signals.manage.send(type, form=request.form)
    return redirect(url_for('.show_list', type=type))


@admin.route('/<path:path>', methods=['GET', 'POST'])
def dispatch(path):
    sidebars = []
    signals.sidebar.send(sidebars=sidebars)
    new_sidebars = []
    signals.new_sidebar.send(new_sidebars=new_sidebars)
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
    return render_template('admin/framework.html', sidebars=sidebars, plugins=Plugin.plugins, templates=templates,
                           scripts=scripts, csss=csss)


@admin.route('/trans-slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
