from .models import PluginProxy
from .models import Plugin

current_plugin = PluginProxy()
plugin_route = Plugin.view_route
plugin_url_for = Plugin.view_url_for
