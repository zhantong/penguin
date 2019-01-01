from ..models import Signal, Component
from .models import Plugin

current_component = Component.current_component()


@Signal.connect('admin', 'sidebar_item')
def sidebar(component, **kwargs):
    if component == current_component:
        return current_component.render_template('items.html', plugins=Plugin.plugins)


@current_component.route('admin', '/*')
def admin_request(path, request, templates, scripts, csss, meta):
    plugin_slug = path.split('/')[0]
    Plugin.find_plugin(plugin_slug).request(path, request=request, templates=templates, scripts=scripts, csss=csss, meta=meta)
