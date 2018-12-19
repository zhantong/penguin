from . import main
from flask import render_template, request, url_for
from ..plugins.models import Plugin

current_plugin = Plugin.current_plugin()

current_plugin.signal.declare_signal('get_navbar_item', return_type='single')
current_plugin.signal.declare_signal('widget', return_type='list')


@main.route('/')
def index():
    left_widgets = []
    right_widgets = []
    main_widgets = []
    widgets = current_plugin.signal.send_this('widget', end_point='.index')
    for widget in widgets:
        if widget['slug'] == 'category':
            left_widgets.append(widget)
        elif widget['slug'] == 'latest_comments':
            right_widgets.append(widget)
    main_widgets.append(Plugin.Signal.send('article', 'get_widget_article_list', request=request))

    return render_template('index.html', main_widgets=main_widgets, left_widgets=left_widgets, right_widgets=right_widgets)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@current_plugin.signal.connect_this('get_navbar_item')
def get_navbar_item(sender, **kwargs):
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
