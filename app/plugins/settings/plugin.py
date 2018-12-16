from ..models import Plugin
from flask import render_template, request, jsonify
from .models import Settings
from ...admin import admin

current_plugin = Plugin.current_plugin()


@Plugin.Signal.connect('penguin', 'deploy')
def deploy(sender, **kwargs):
    current_plugin.set_setting('site_name', name='站名', value='Penguin', value_type='str')
    current_plugin.set_setting('items_per_page', name='每页项目数', value='20', value_type='int')


@current_plugin.route('admin', '/settings', '通用')
def general(templates, scripts, **kwargs):
    widget = current_plugin.signal.send_this('get_widget_list', category=current_plugin.slug, meta={'plugin': current_plugin.slug})
    templates.append(widget['html'])
    scripts.append(widget['script'])


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
    settings = Settings.query.filter_by(category=category, visibility='visible').all()
    return {
        'slug': 'settings',
        'name': '设置',
        'html': render_template(current_plugin.template_path('widget_list', 'widget.html'), settings=settings, category=category, meta=meta),
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
