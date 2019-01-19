from flask import render_template, request

from bearblog import current_component, component_url_for, component_route
from bearblog.models import Signal
from bearblog.settings import get_setting

Signal = Signal(None)
Signal.set_default_scope(current_component.slug)


@component_route('/', 'index')
def index():
    widgets = Signal.send('widget', end_point='.index', request=request)
    main_widgets = widgets['main']
    left_widgets = widgets['left']
    right_widgets = widgets['right']

    return render_template('index.html', main_widgets=main_widgets, left_widgets=left_widgets, right_widgets=right_widgets)


@Signal.connect('sidebar_item', 'admin')
def admin_sidebar_item():
    return {
        'name': current_component.name,
        'slug': current_component.slug,
        'items': [
            {
                'type': 'link',
                'name': '通用',
                'url': component_url_for('main_settings', 'admin')
            }
        ]
    }


@Signal.connect('index_url')
def index_url(**kwargs):
    return current_component.view_url_for('index', **kwargs)


@current_component.blueprint.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@current_component.blueprint.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@Signal.connect('create_app', 'bearblog')
def create_app(app):
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

            navbar_items = Signal.send('navbar_item')
            for navbar_item in navbar_items:
                process_item(navbar_item)

            return custom_navbar

        return dict(custom_navbar=custom_navbar)


@Signal.connect('navbar_item')
def get_navbar_item():
    return {
        'type': 'brand',
        'brand': get_setting('site_name').value,
        'more': [
            {
                'type': 'item',
                'name': '首页',
                'link': component_url_for('index')
            }
        ]
    }


@component_route('/main/settings', 'main_settings', 'admin')
def account():
    return Signal.send('get_rendered_settings', 'settings', category=current_component.slug, meta={'plugin': current_component.slug})
