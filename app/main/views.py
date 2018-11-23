from . import main
from flask import render_template, request, url_for
from ..plugins.article import signals as article_signals
from ..plugins.comment import signals as comment_signals
from . import signals
from ..plugins.settings.plugin import get_setting


@main.route('/')
def index():
    left_widgets = []
    right_widgets = []
    main_widgets = []

    widget = {'widget': None}
    article_signals.get_widget_category_list.send(widget=widget)
    left_widgets.append(widget['widget'])
    comment_signals.get_widget_latest_comments.send(widget=widget)
    right_widgets.append(widget['widget'])
    article_signals.get_widget_article_list.send(widget=widget, request=request)
    main_widgets.append(widget['widget'])

    return render_template('index.html', main_widgets=main_widgets, left_widgets=left_widgets,
                           right_widgets=right_widgets)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@signals.get_navbar_item.connect
def get_navbar_item(sender, item, **kwargs):
    item['item'] = {
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
