from . import main
from . import signals
from flask import request, render_template


@main.route('/')
def index():
    contents = []
    left_widgets = []
    right_widgets = []
    scripts = []
    styles = []
    signals.index.send(request=request, contents=contents, left_widgets=left_widgets,
                       right_widgets=right_widgets, scripts=scripts, styles=styles)
    return render_template('index.html', contents=contents, left_widgets=left_widgets, right_widgets=right_widgets,
                           scripts=scripts, styles=styles)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
