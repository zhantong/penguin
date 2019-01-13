from bearblog import current_component
from .models import Plugin
from bearblog.models import Signal


@Signal.connect('admin', 'sidebar_item')
def sidebar_item():
    return current_component.signal.send_this('admin_sidebar_item')


@current_component.route('admin', '/*')
def admin_request(path, request, templates, scripts, csss, meta):
    plugin_slug = path.split('/')[0]
    Plugin.find_plugin(plugin_slug).request(path, request=request, templates=templates, scripts=scripts, csss=csss, meta=meta)
