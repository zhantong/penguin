from flask import url_for
from urllib.parse import urlencode


class Plugin:
    plugins = {}

    @staticmethod
    def find_plugin(slug):
        return Plugin.plugins[slug]

    def __init__(self, name, slug):
        Plugin.plugins[slug] = self
        self.name = name
        self.slug = slug
        self.routes = {}

    def route(self, blueprint, rule, name=None, **kwargs):
        def wrap(f):
            self.routes[rule] = Route(self, blueprint, rule, f, name)
            return f

        return wrap

    def request(self, path, **kwargs):
        rule = '/' + path.split('/')[1]
        self.routes[rule].func(**kwargs)

    def url_for(self, rule, **values):
        return self.routes[rule].path() + '?' + urlencode(values)


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=None):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.dispatch', path=self.plugin.slug + self.rule)
