from flask import render_template, request, redirect, url_for, jsonify
from flask_login import login_required
from . import admin
from ..utils import slugify
from blinker import signal


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    sidebars = []
    signal('sidebar').send(sidebars=sidebars)
    return render_template('admin/index.html', sidebars=sidebars)


@admin.route('/edit')
def edit():
    type = request.args['type']
    context = {}
    styles = []
    hiddens = []
    contents = []
    widgets = []
    scripts = []
    result = signal('edit').send(type, args=request.args, context=context, styles=styles, hiddens=hiddens,
                                 contents=contents, widgets=widgets,
                                 scripts=scripts)
    sidebars = []
    signal('sidebar').send(sidebars=sidebars)
    return render_template('admin/edit.html', **request.args.to_dict(), **context, sidebars=sidebars, styles=styles,
                           hiddens=hiddens,
                           contents=contents, widgets=widgets,
                           scripts=scripts)


@admin.route('/edit', methods=['POST'])
def submit():
    type = request.form['type']
    result = signal('submit').send(type, form=request.form)
    return redirect(url_for('.show_list', type=type))


@admin.route('/manage')
def show_list():
    type = request.args['type']
    result = signal('show_list').send(type, args=request.args)
    context = result[0][1]
    sidebars = []
    signal('sidebar').send(sidebars=sidebars)
    return render_template('admin/manage.html', **context, sidebars=sidebars)


@admin.route('/manage', methods=['POST'])
def manage():
    type = request.form['type']
    result = signal('manage').send(type, form=request.form)
    return redirect(url_for('.show_list', type=type))


@admin.route('/trans-slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })
