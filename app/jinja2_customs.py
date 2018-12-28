import jinja2
from .plugins.models import Plugin


def custom(app):
    @app.template_test('list')
    def test_list(l):
        return isinstance(l, list)

    @app.template_filter('type')
    def filter_type(t):
        return type(t)

    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.FileSystemLoader(['app/plugins'])
    ])

    @app.context_processor
    def context_processor():
        return dict(
            get_setting=Plugin.get_setting,
            get_setting_value=Plugin.get_setting_value)
