from flask import request

from bearblog import component_route
from .models import Page
from bearblog.models import Signal
from bearblog.plugins import current_plugin

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/page/<string:slug>', 'page', 'api')
def page(slug):
    page = Page.query.filter_by(slug=slug).order_by(Page.version_timestamp.desc())
    if 'version' in request.args:
        page = page.filter_by(number=request.args['version'])
    page = page.first()
    return page.to_json(level='full')


@component_route('/pages', 'pages', 'api')
def pages():
    pages = Page.query.all()
    more = []
    for page in pages:
        more.append({
            'title': page.title,
            'slug': page.slug
        })
    dynamic_pages = Signal.send('dynamic_page')
    for page in dynamic_pages:
        more.append({
            'title': page['title'],
            'slug': page['slug']
        })
    return {'pages': more}
