from . import main
from flask import render_template
from ..plugins.article import signals as article_signals
from ..plugins.comment import signals as comment_signals


@main.route('/')
def index():
    contents = []
    left_widgets = []
    right_widgets = []

    widget = {'widget': None}
    article_signals.get_widget_category_list.send(widget=widget)
    left_widgets.append(widget['widget'])
    comment_signals.get_widget_latest_comments.send(widget=widget)
    right_widgets.append(widget['widget'])

    scripts = []
    styles = []
    # signals.index.send(request=request, contents=contents, left_widgets=left_widgets,
    #                    right_widgets=right_widgets, scripts=scripts, styles=styles)
    return render_template('index.html', contents=contents, left_widgets=left_widgets, right_widgets=right_widgets,
                           scripts=scripts, styles=styles)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
