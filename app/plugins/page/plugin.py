from ..models import Plugin

page = Plugin('页面', 'page')
page_instance = page

from . import signals
from ...main import main
from flask import render_template, url_for, request, session, make_response
from ...signals import navbar
from ...signals import restore
from datetime import datetime
from ...models import db, User
from pathlib import Path
from .models import Page
from ..comment import signals as comment_signals
from ..template import signals as template_signals
import json


@main.route('/<string:slug>.html')
def show_page(slug):
    def get_pages(repository_id):
        return Page.query.filter_by(repository_id=repository_id).order_by(Page.timestamp.desc()).all()

    page = Page.query.filter_by(slug=slug).order_by(Page.version_timestamp.desc())
    if 'version' in request.args:
        page = page.filter_by(number=request.args['version'])
    page = page.first_or_404()
    left_widgets = []
    right_widgets = []
    scripts = []
    styles = []
    cookies_to_set = {}
    rendered_comments = {}
    comment_signals.get_rendered_comments.send(session=session, comments=page.comments,
                                               rendered_comments=rendered_comments,
                                               scripts=scripts, styles=styles,
                                               meta={'type': 'page', 'page_id': page.id})
    rendered_comments = rendered_comments['rendered_comments']
    signals.show.send(request=request, page=page, cookies_to_set=cookies_to_set, left_widgets=left_widgets,
                      right_widgets=right_widgets, scripts=scripts, styles=styles)
    if page.template is not None:
        html = {}
        template_signals.render_template.send(template=page.template, json_params=json.loads(page.body),
                                              html=html)
        page.body_html = html['html']
    resp = make_response(render_template(Path('page', 'templates', 'page.html').as_posix(), page=page,
                                         rendered_comments=rendered_comments, left_widgets=left_widgets,
                                         right_widgets=right_widgets, scripts=scripts, styles=styles,
                                         get_pages=get_pages))
    for key, value in cookies_to_set.items():
        resp.set_cookie(key, value)
    return resp


@navbar.connect
def navbar(sender, content):
    pages = Page.query.all()
    content['items'].extend((page.title, url_for('main.show_page', slug=page.slug)) for page in pages)


@restore.connect
def restore(sender, data, directory, **kwargs):
    if 'page' in data:
        pages = data['page']
        for page in pages:
            p = Page(title=page['title'], slug=page['slug'], body=page['body'],
                     timestamp=datetime.utcfromtimestamp(page['timestamp']), status=page['version']['status'],
                     repository_id=page['version']['repository_id'],
                     author=User.query.filter_by(username=page['author']).one())
            db.session.add(p)
            db.session.flush()
            if 'comments' in page:
                restored_comments = []
                comment_signals.restore.send(comments=page['comments'], restored_comments=restored_comments)
                p.comments = restored_comments
                db.session.flush()
            signals.restore.send(data=page, directory=directory, page=p)


@comment_signals.get_comment_show_info.connect
def get_comment_show_info(sender, comment, anchor, info, **kwargs):
    if comment.page is not None:
        info['title'] = comment.page.title
        info['url'] = url_for('main.show_page', slug=comment.page.slug, _anchor=anchor)
