import json

from flask import request, jsonify

from bearblog import current_component, component_route, component_url_for
from .models import Settings
from bearblog.models import Component, Signal

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@Signal.connect('deploy', 'bearblog')
def deploy():
    Settings.set_setting('site_name', 'settings', name='站名', value='BearBlog', value_type='str')
    Settings.set_setting('items_per_page', 'settings', name='每页项目数', value='20', value_type='int')


@Signal.connect('sidebar_item', 'admin')
def admin_sidebar_item():
    return {
        'name': current_component.name,
        'slug': current_component.slug,
        'items': [
            {
                'type': 'link',
                'name': '通用',
                'url': component_url_for('settings_settings', 'admin')
            }
        ]
    }


@component_route('/settings/settings', 'settings_settings', 'admin')
def get_settings():
    return Signal.send('get_rendered_settings', category=current_component.slug, meta={'plugin': current_component.slug})


@Signal.connect('get_rendered_settings')
def get_widget_list(category, meta, signals=None):
    for signal_name, data in (signals or {}).items():
        if data.get('managed', False):
            if 'return_type' in data and data['return_type'] == 'list':
                if Settings.get_setting(signal_name) is None:
                    value = {
                        'subscribers_order': {
                            'main': []
                        },
                        'subscribers': {}
                    }
                    Settings.set_setting(signal_name, category, name=signal_name, value=json.dumps(value), value_type='signal')
                value = Settings.get_setting(signal_name, category).value
                if 'custom_list' in data:
                    value['subscribers_order'] = {list_key: list_value for list_key, list_value in value['subscribers_order'].items() if list_key in data['custom_list']}
                    for custom_list_key in data['custom_list'].keys():
                        if custom_list_key not in value['subscribers_order']:
                            value['subscribers_order'][custom_list_key] = []
                for list_key in value['subscribers_order'].keys():
                    value['subscribers_order'][list_key] = [item for item in value['subscribers_order'][list_key] if item['subscriber'] in signals[signal_name]['receivers']]
                for key, info in signals[signal_name].get('receivers', {}).items():
                    if key not in value['subscribers']:
                        value['subscribers'][key] = {
                            'file': info['func_file'],
                        }
                        for custom_list_key, custom_list in value['subscribers_order'].items():
                            custom_list.append({
                                'subscriber': key,
                                'is_on': data['managed_default'] == 'all'
                            })
                Settings.set_setting(signal_name, category, value=json.dumps(value))

    settings = Settings.query.filter_by(category=category, visibility='visible').all()
    return current_component.render_template('settings.html', settings=settings, category=category, meta=meta)


@component_route('/settings', 'submit_settings', 'admin', methods=['POST'])
def submit_settings():
    category = request.form['category']
    settings = json.loads(request.form['settings'])
    for slug, data in settings.items():
        setting = Settings.get_setting(slug, category)
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
            Settings.set_setting(slug, category, value=json.dumps(value))
    return jsonify({
        'code': 0,
        'message': '更新成功'
    })
