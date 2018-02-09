import jinja2
from . import signals


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
        def custom_navbar():
            content = {
                'brand': 'brand',
                'items': [],
                'others': []
            }
            signals.navbar.send(content=content)
            return content

        return dict(custom_navbar=custom_navbar)
