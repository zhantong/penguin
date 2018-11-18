import jinja2
from .main import signals as main_signals
from .plugins.article import signals as article_signals
from .plugins.article_contents import signals as article_contents_signals
from .plugins.page import signals as page_signals


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

            item = {}
            main_signals.get_navbar_item.send(item=item)
            process_item(item['item'])
            article_signals.get_navbar_item.send(item=item)
            process_item(item['item'])
            article_contents_signals.get_navbar_item.send(item=item)
            process_item(item['item'])
            page_signals.get_navbar_item.send(item=item)
            process_item(item['item'])

            return custom_navbar

        return dict(custom_navbar=custom_navbar)
