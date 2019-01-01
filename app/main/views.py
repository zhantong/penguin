from . import main
from flask import render_template, request, url_for
from ..plugins.models import Plugin
from ..models import Signal, Component

current_component = Component.current_component()


@main.route('/')
def index():
    widgets = current_component.signal.send_this('widget', end_point='.index', request=request)
    main_widgets = widgets['main']
    left_widgets = widgets['left']
    right_widgets = widgets['right']

    return render_template('index.html', main_widgets=main_widgets, left_widgets=left_widgets, right_widgets=right_widgets)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@Signal.connect('penguin', 'create_app')
def create_app(app, **kwargs):
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

            navbar_items = current_component.signal.send_this('navbar_item')
            for navbar_item in navbar_items:
                process_item(navbar_item)

            return custom_navbar

        return dict(custom_navbar=custom_navbar)


@current_component.signal.connect_this('navbar_item')
def get_navbar_item(**kwargs):
    return {
        'type': 'brand',
        'brand': Plugin.get_setting_value('site_name'),
        'more': [
            {
                'type': 'item',
                'name': '首页',
                'link': url_for('main.index')
            }
        ]
    }


@current_component.route('admin', '/settings', '设置')
def account(request, templates, scripts, **kwargs):
    widget = Signal.send('settings', 'get_widget_list', category=current_component.slug, meta={'plugin': current_component.slug})
    templates.append(widget['html'])
    scripts.append(widget['script'])
