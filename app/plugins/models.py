from flask import url_for, render_template
from urllib.parse import urlencode
from pathlib import Path
import blinker
import inspect
import os


class Plugin:
    plugins = {}

    class Signal:
        signals = {}

        def __init__(self, outer_class):
            self.outer_class = outer_class

        @staticmethod
        def connect(plugin_name, name):
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            signal_name = plugin_name + '.' + name
            if signal_name not in Plugin.Signal.signals:
                Plugin.Signal.signals[signal_name] = {}
            if 'connect' not in Plugin.Signal.signals[signal_name]:
                Plugin.Signal.signals[signal_name]['connect'] = []
            Plugin.Signal.signals[signal_name]['connect'].append(caller)
            signal = blinker.signal(signal_name)
            return signal.connect

        def connect_this(self, name):
            caller = inspect.getframeinfo(inspect.stack()[1][0])
            signal_name = self.outer_class.slug + '.' + name
            if signal_name not in Plugin.Signal.signals:
                Plugin.Signal.signals[signal_name] = {}
            if 'connect' not in Plugin.Signal.signals[signal_name]:
                Plugin.Signal.signals[signal_name]['connect'] = []
            Plugin.Signal.signals[signal_name]['connect'].append(caller)
            signal = blinker.signal(signal_name)
            return signal.connect

        @staticmethod
        def send(plugin_name, name, **kwargs):
            signal_name = plugin_name + '.' + name
            signal = blinker.signal(signal_name)
            result = signal.send(**kwargs)
            if 'return_type' in Plugin.Signal.signals[signal_name]:
                return_type = Plugin.Signal.signals[signal_name]['return_type']
                if return_type == 'single':
                    return result[0][1]
                if return_type == 'list':
                    return [item[1] for item in result]
                if return_type == 'merged_list':
                    items = []
                    for item in result:
                        if type(item[1]) is list:
                            items.extend(item[1])
                        else:
                            items.append(item[1])
                    return items
                if return_type == 'single_not_none':
                    for item in result:
                        if item[1] is not None:
                            return item[1]

        def send_this(self, name, **kwargs):
            return Plugin.Signal.send(self.outer_class.slug, name, **kwargs)

        def declare_signal(self, name, return_type=None):
            signal_name = self.outer_class.slug + '.' + name
            if signal_name not in Plugin.Signal.signals:
                Plugin.Signal.signals[signal_name] = {}
            Plugin.Signal.signals[signal_name]['return_type'] = return_type

    @staticmethod
    def find_plugin(slug):
        return Plugin.plugins[slug]

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
        self.signal = self.Signal(self)
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
        from .settings.plugin import get_setting_value
        return get_setting_value(key, category=plugin_name, default=default)

    @staticmethod
    def get_setting(key, plugin_name=None):
        from .settings.plugin import get_setting
        return get_setting(key, category=plugin_name)

    def get_setting_value_this(self, key, default=None):
        return Plugin.get_setting_value(key, self.slug, default=default)

    def get_setting_this(self, key):
        return Plugin.get_setting(key, self.slug)

    def set_setting(self, key, **kwargs):
        from .settings.plugin import set_setting
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
        return url_for(self.blueprint + '.dispatch', path=self.plugin.slug + self.rule)
