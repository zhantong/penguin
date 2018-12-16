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
        def custom_navbar():
            custom_navbar = {
                'brand': '',
                'items': [],
                'templates': []
            }

            def process_item(item):
                def insert_item(item):
                    if item['type'] == 'brand':
                        custom_navbar['brand'] = item['brand']
                    elif item['type'] == 'item':
                        item.pop('type')
                        custom_navbar['items'].append(item)
                    elif item['type'] == 'template':
                        item.pop('type')
                        custom_navbar['templates'].append(item)

                more = item.pop('more', None)
                if 'type' in item:
                    insert_item(item)
                if more is not None:
                    for item in more:
                        insert_item(item)

            process_item(Plugin.Signal.send('main', 'get_navbar_item'))
            process_item(Plugin.Signal.send('article', 'get_navbar_item'))
            process_item(Plugin.Signal.send('page', 'get_navbar_item'))

            return custom_navbar

        return dict(custom_navbar=custom_navbar,
                    get_setting=Plugin.get_setting,
                    get_setting_value=Plugin.get_setting_value)
