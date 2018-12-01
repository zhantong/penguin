from . import main
from flask import render_template, request, url_for
from ..plugins.settings.plugin import get_setting
from ..plugins.models import Plugin

main_instance = Plugin('main', 'main', show_in_sidebar=False)

main_instance.signal.declare_signal('get_navbar_item', return_type='single')


@main.route('/')
def index():
    left_widgets = []
    right_widgets = []
    main_widgets = []

    left_widgets.append(Plugin.Signal.send('article', 'get_widget_category_list'))
    right_widgets.append(Plugin.Signal.send('comment', 'get_widget_latest_comments'))
    main_widgets.append(Plugin.Signal.send('article', 'get_widget_article_list', request=request))

    return render_template('index.html', main_widgets=main_widgets, left_widgets=left_widgets,
                           right_widgets=right_widgets)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@main_instance.signal.connect_this('get_navbar_item')
def get_navbar_item(sender, **kwargs):
    return {
        'type': 'brand',
        'brand': get_setting('site_name'),
        'more': [
            {
                'type': 'item',
                'name': '首页',
                'link': url_for('main.index')
            }
        ]
    }
