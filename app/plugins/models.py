from flask import url_for, render_template
from urllib.parse import urlencode
from pathlib import Path
import inspect
import os
from ..models import Signal, Component


class Plugin:
    plugins = {}
    Component._component_search_scope.append(plugins)

    @staticmethod
    def find_plugin(slug):
        return Plugin.plugins.get(slug, None)

    def __init__(self, name, directory, slug=None, show_in_sidebar=True):
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

    def route(self, blueprint, rule, name=None, **kwargs):
        def wrap(f):
            self.routes[rule] = Route(self, blueprint, rule, f, name)
            return f

        return wrap

    def request(self, path, **kwargs):
        rule = '/' + path.split('/')[1]
        self.routes[rule].func(**kwargs)

    def url_for(self, rule, **values):
        if len(values) == 0:
            return self.routes[rule].path()
        return self.routes[rule].path() + '?' + urlencode(values)

    def template_path(self, *args):
        return Path(self.slug, 'templates', *args).as_posix()

    @staticmethod
    def current_plugin():
        caller = inspect.getframeinfo(inspect.stack()[1][0])
        caller_path = caller.filename
        caller_path_comp = caller_path.split(os.sep)
        if 'plugins' in caller_path_comp:
            plugin_slug = caller_path_comp[caller_path_comp.index('plugins') + 1]

        else:
            plugin_slug = Path(caller_path).parent.name
        return Plugin.plugins[plugin_slug]

    @staticmethod
    def get_setting_value(key, plugin_name=None, default=None):
        from app.settings import get_setting_value
        return get_setting_value(key, category=plugin_name, default=default)

    @staticmethod
    def get_setting(key, plugin_name=None):
        from app.settings import get_setting
        return get_setting(key, category=plugin_name)

    def get_setting_value_this(self, key, default=None):
        return Plugin.get_setting_value(key, self.slug, default=default)

    def get_setting_this(self, key):
        return Plugin.get_setting(key, self.slug)

    def set_setting(self, key, **kwargs):
        from app.settings import set_setting
        return set_setting(key, self.slug, **kwargs)

    def render_template(self, *args, **kwargs):
        return render_template(self.template_path(*args), **self.template_context, **kwargs)

    def context_func(self, f):
        self.template_context[f.__name__] = f
        return f


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=None):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.dispatch', path='plugins/' + self.plugin.slug + self.rule)
