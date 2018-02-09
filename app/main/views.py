from . import main
from . import signals
from flask import request, render_template


@main.route('/')
def index():
    context = {}
    styles = []
    contents = []
    left_widgets = []
    right_widgets = []
    scripts = []
    signals.index.send(args=request.args, context=context, styles=styles, contents=contents, left_widgets=left_widgets,
                       right_widgets=right_widgets, scripts=scripts)
    return render_template('index.html', **request.args.to_dict(), **context, styles=styles, contents=contents,
                           left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts)


@main.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
