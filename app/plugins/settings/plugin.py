from ..models import Plugin
from flask import render_template, current_app, request, jsonify
from .models import Settings
from ...admin import admin

current_plugin = Plugin.current_plugin()

current_plugin.signal.declare_signal('get_widget_list', return_type='single')


@Plugin.Signal.connect('penguin', 'deploy')
def deploy(sender, **kwargs):
    current_plugin.set_setting('site_name', name='站名', value='Penguin', value_type='str')


@current_plugin.route('admin', '/settings', '通用')
def general(request, templates, **kwargs):
    if request.method == 'GET':
        site_name = Settings.get('site_name')

        templates.append(render_template(current_plugin.template_path('general.html'), site_name=site_name))
    elif request.method == 'POST':
        def reload():
            current_app.config['SITE_NAME'] = Settings.get('site_name')

        site_name = request.form.get('site-name', type=str)

        Settings.set('site_name', site_name)

        reload()


def get_setting(slug, category=None):
    if category is None:
        category = current_plugin.slug
    return Settings.get(slug, category)


def get_setting_value(slug, category=None, default=None):
    if category is None:
        category = current_plugin.slug
    value = Settings.get_value(slug, category)
    if value is None:
        value = default
    return value


def set_setting(key, category='settings', **kwargs):
    Settings.set(key, category, **kwargs)


@current_plugin.signal.connect_this('get_widget_list')
def get_widget_list(sender, category, meta, **kwargs):
    settings = Settings.query.filter_by(category=category).all()
    return {
        'slug': 'settings',
        'name': '设置',
        'html': render_template(current_plugin.template_path('widget_list', 'widget.html'), settings=settings,
                                category=category, meta=meta),
        'script': render_template(current_plugin.template_path('widget_list', 'widget.js.html'))
    }


@admin.route('/settings', methods=['POST'])
def submit_settings():
    meta = {}
    for slug, value in request.form.items():
        if slug == '_category':
            category = value
    for slug, value in request.form.items():
        if slug == 'csrf_token' or slug == '_category':
            continue
        if slug.startswith('_meta_'):
            key = slug[len('_meta_')]
            meta[key] = value
        else:
            set_setting(slug, category, value=value)
    return jsonify({
        'code': 0,
        'message': '更新成功'
    })
