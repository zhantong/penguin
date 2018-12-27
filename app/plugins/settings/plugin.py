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
                        'subscribers_order': {
                            'main': []
                        },
                        'subscribers': {}
                    }
                    plugin.set_setting(signal_name, name=signal_name, value=json.dumps(value), value_type='signal')
                value = plugin.get_setting_value_this(signal_name)
                if 'custom_list' in data:
                    for list_key in value['subscribers_order'].keys():
                        if list_key not in data['custom_list']:
                            del value['subscribers_order'][list_key]
                    for custom_list_key in data['custom_list'].keys():
                        if custom_list_key not in value['subscribers_order']:
                            value['subscribers_order'][custom_list_key] = []
                for list_key in value['subscribers_order'].keys():
                    value['subscribers_order'][list_key] = [item for item in value['subscribers_order'][list_key] if item['subscriber'] in plugin.signal.signals[signal_name]['receivers']]
                for key, info in plugin.signal.signals[signal_name]['receivers'].items():
                    if key not in value['subscribers']:
                        value['subscribers'][key] = {
                            'file': info['func_file'],
                        }
                        for custom_list_key, custom_list in value['subscribers_order'].items():
                            custom_list.append({
                                'subscriber': key,
                                'is_on': data['managed_default'] == 'all'
                            })
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
            on_sets = {}
            for item in data[::-1]:
                value['subscribers_order'][item['name']].insert(0, value['subscribers_order'][item['name']].pop(next((index for (index, d) in enumerate(value['subscribers_order'][item['name']]) if d['subscriber'] == item['value']))))
                value['subscribers_order'][item['name']][0]['is_on'] = True
                if item['name'] not in on_sets:
                    on_sets[item['name']] = set()
                on_sets[item['name']].add(item['value'])
            for list_name, items in value['subscribers_order'].items():
                for item in items:
                    if list_name not in on_sets or item['subscriber'] not in on_sets[list_name]:
                        item['is_on'] = False
            set_setting(slug, category, value=json.dumps(value))
    return jsonify({
        'code': 0,
        'message': '更新成功'
    })
