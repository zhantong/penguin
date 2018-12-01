from ..models import Plugin
from flask import render_template, current_app
from .models import Settings

settings = Plugin('设置', 'settings')
settings_instance = settings


@Plugin.Signal.connect('penguin', 'deploy')
def deploy(sender, **kwargs):
    Settings.set('site_name', 'Penguin')


@settings.route('admin', '/settings', '通用')
def general(request, templates, **kwargs):
    if request.method == 'GET':
        site_name = Settings.get('site_name')

        templates.append(render_template(settings_instance.template_path('general.html'), site_name=site_name))
    elif request.method == 'POST':
        def reload():
            current_app.config['SITE_NAME'] = Settings.get('site_name')

        site_name = request.form.get('site-name', type=str)

        Settings.set('site_name', site_name)

        reload()


def get_setting(key, type=None, default=None):
    value = Settings.get(key)
    if value is None:
        if default is None:
            raise ValueError()
        value = default
    if type is not None:
        value = type(value)
    return value
