from ..models import Signal
from .models import Plugin
from app import current_component


@Signal.connect('admin', 'sidebar_item')
def sidebar(component):
    if component == current_component:
        return current_component.render_template('items.html', plugins=Plugin.plugins)


@current_component.route('admin', '/*')
def admin_request(path, request, templates, scripts, csss, meta):
    plugin_slug = path.split('/')[0]
    Plugin.find_plugin(plugin_slug).request(path, request=request, templates=templates, scripts=scripts, csss=csss, meta=meta)
