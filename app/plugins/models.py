from flask import url_for
from urllib.parse import urlencode
from pathlib import Path
import blinker
import inspect


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
    def find_plugin(slug):
        return Plugin.plugins[slug]

    def __init__(self, name, slug):
        Plugin.plugins[slug] = self
        self.name = name
        self.slug = slug
        self.routes = {}
        self.signal = self.Signal(self)

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


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=None):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.dispatch', path=self.plugin.slug + self.rule)
