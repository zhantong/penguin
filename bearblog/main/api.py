from bearblog import current_component, component_route
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@component_route('/navbar', 'navbar', 'api')
def navbar():
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

    navbar_items = Signal.send('navbar_item')
    for navbar_item in navbar_items:
        process_item(navbar_item)
    return custom_navbar
