from ..models import Plugin
from flask import render_template, current_app
from .models import Settings

current_plugin = Plugin.current_plugin()


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
