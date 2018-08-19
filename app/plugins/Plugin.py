from flask import url_for


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

    def route(self, blueprint, rule, name='', **kwargs):
        def wrap(f):
            self.routes[rule] = Route(self, blueprint, rule, f, name)
            return f

        return wrap

    def request(self, path, **kwargs):
        rule = '/' + path.split('/')[1]
        self.routes[rule].func(**kwargs)


class Route:
    def __init__(self, plugin, blueprint, rule, func, name=''):
        self.plugin = plugin
        self.blueprint = blueprint
        self.rule = rule
        self.func = func
        self.name = name

    def path(self):
        return url_for(self.blueprint + '.dispatch', path=self.plugin.slug + self.rule)
