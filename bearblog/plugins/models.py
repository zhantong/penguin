import inspect
import sys
import os.path
from pathlib import Path
from urllib.parse import urlencode

from flask import url_for, render_template, request
from werkzeug.routing import Map

from bearblog.models import Signal, Component
from bearblog import component_route
from bearblog.settings import add_default_cateogry


class Plugin:
    plugins = {}

    component = Component.find_component('plugins')

    @staticmethod
    def find_plugin(slug):
        return Plugin.plugins.get(slug, None)

    def __init__(self, name, directory, slug=None, show_in_sidebar=True, config=None):
        if slug is None:
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            caller_path = caller.filename
            slug = Path(caller_path).parent.name
        Plugin.plugins[slug] = self
        self.name = name
        self.slug = slug
        self.directory = directory
        self.show_in_sidebar = show_in_sidebar
        self.routes = {}
        self.signal = Signal(self)
        self.template_context = {}
        self.rule_map = Map()
        self.view_functions = {}
        self.config = config or {}

        if 'default_setting_category' in self.config:
            add_default_cateogry(self.directory, self.config['default_setting_category'])

    def setup(self):
        self.urls = self.rule_map.bind('', '/')

        @component_route('/' + self.slug + '/<path:path>', endpoint=self.slug, component='plugins', methods=['GET', 'POST'])
        def route(path):
            endpoint, params = self.urls.match('/' + path, method=request.method)
            return self.view_functions[endpoint](**params)

    def route(self, blueprint, rule, name=None, **kwargs):
        def wrap(f):
            self.routes[rule] = Route(self, blueprint, rule, f, name)
            return f

        return wrap

    @classmethod
    def view_route(cls, rule, endpoint, plugin=None, _component='plugins', **kwargs):
        if plugin is None:
            plugin = PluginProxy._get_current_object()
        else:
            plugin = cls.find_plugin(plugin)
        return plugin._instance_view_route(rule, endpoint, _component=_component, **kwargs)

    def _instance_view_route(self, rule, endpoint, _component='plugins', **kwargs):
        def wrap(f):
            Component.view_route('/plugins/' + self.slug + rule, 'plugins_' + self.slug + '_' + endpoint, _component, **kwargs)(f)

        return wrap

    def request(self, path, **kwargs):
        rule = '/' + path.split('/')[1]
        self.routes[rule].func(**kwargs)

    def url_for(self, rule, **values):
        if len(values) == 0:
            return self.routes[rule].path()
        return self.routes[rule].path() + '?' + urlencode(values)

    @classmethod
    def view_url_for(cls, endpoint, plugin=None, _component='plugins', **kwargs):
        if plugin is None:
            plugin = PluginProxy._get_current_object()
        else:
            plugin = cls.find_plugin(plugin)

        return plugin._instance_view_url_for(endpoint, _component, **kwargs)

    def _instance_view_url_for(self, endpoint, _component='plugins', **kwargs):
        return Component.view_url_for('plugins_' + self.slug + '_' + endpoint, _component, **kwargs)

    def template_path(self, *args):
        return Path(self.slug, 'templates', *args).as_posix()

    def render_template(self, *args, **kwargs):
        return render_template(self.template_path(*args), **self.template_context, **kwargs)

    def context_func(self, f):
        self.template_context[f.__name__] = f
        return f


class PluginProxy:
    root_path = Path(__file__).parent

    def __getattr__(self, item):
        return getattr(self._get_current_object(), item)

    def __eq__(self, other):
        return self._get_current_object() == other

    @classmethod
    def _get_current_object(cls):
        frame = sys._getframe()
        while frame is not None:
            path = os.path.abspath(frame.f_code.co_filename)
            if path.startswith(str(cls.root_path)):
                path = Path(path).relative_to(cls.root_path)
                plugin_slug = path.parts[0]
                if plugin_slug in Plugin.plugins:
                    return Plugin.plugins[plugin_slug]
            frame = frame.f_back


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=None):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.route', path='plugins/' + self.plugin.slug + self.rule)
