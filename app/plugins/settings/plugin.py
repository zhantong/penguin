from ..models import Plugin
from flask import request, jsonify
from .models import Settings
from ...admin import admin
import json

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


def get_setting_obj(slug, category=None):
    return Settings.query.filter_by(slug=slug, category=category).first()


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
    plugin = Plugin.find_plugin(category)
    for signal_name, data in plugin.signal.signals.items():
        if data.get('managed', False):
            if 'return_type' in data and data['return_type'] == 'list':
                if plugin.get_setting_this(signal_name) is None:
                    value = {
                        'subscribers_order': [],
                        'subscribers': {}
                    }
                    plugin.set_setting(signal_name, name=signal_name, value=json.dumps(value), value_type='signal')
                value = plugin.get_setting_value_this(signal_name)
                for key, info in plugin.signal.signals[signal_name]['receivers'].items():
                    if key not in value['subscribers']:
                        value['subscribers_order'].append(key)
                        value['subscribers'][key] = {
                            'file': info['func_file'],
                            'is_on': data['managed_default'] == 'all'
                        }
                plugin.set_setting(signal_name, value=json.dumps(value))

    settings = Settings.query.filter_by(category=category, visibility='visible').all()
    return {
        'slug': 'settings',
        'name': '设置',
        'html': current_plugin.render_template('widget_list', 'widget.html', settings=settings, category=category, meta=meta),
        'script': current_plugin.render_template('widget_list', 'widget.js.html', category=category)
    }


@admin.route('/settings', methods=['POST'])
def submit_settings():
    category = request.form['category']
    settings = json.loads(request.form['settings'])
    for slug, data in settings.items():
        setting = get_setting_obj(slug, category)
        if setting.value_type == 'signal':
            value = setting.get_value_self()
            on_set = set()
            on_list = []
            for item in data:
                if item['name'] == 'subscriber_key':
                    on_set.add(item['value'])
                    on_list.append(item['value'])
                    value['subscribers'][item['value']]['is_on'] = True
            for subscriber_key in value['subscribers'].keys():
                value['subscribers'][subscriber_key]['is_on'] = subscriber_key in on_set
            for subscriber_key in on_list[::-1]:
                value['subscribers_order'].insert(0, value['subscribers_order'].pop(value['subscribers_order'].index(subscriber_key)))
            set_setting(slug, category, value=json.dumps(value))
    return jsonify({
        'code': 0,
        'message': '更新成功'
    })
