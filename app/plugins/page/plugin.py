from . import signals
from ...main import main
from flask import render_template, url_for
from ...signals import navbar
from ...admin.signals import sidebar
from ...signals import restore
from datetime import datetime
from ...models import db, User
from ...plugins import add_template_file
from pathlib import Path
from .models import Page, Status
from ..comment import signals as comment_signals


@main.route('/<string:slug>.html')
def show_page(slug):
    post = Page.query.filter_by(slug=slug).first_or_404()
    context = {}
    contents = []
    scripts = []
    page_content = {'page_content': Path('page', 'templates', 'page_content.html').as_posix()}
    signals.page.send(post=post, context=context, page_content=page_content, contents=contents, scripts=scripts)
    return render_template(Path('page', 'templates', 'page.html').as_posix(), **context, post=post,
                           page_content=page_content['page_content'], contents=contents, scripts=scripts)


@navbar.connect
def navbar(sender, content):
    pages = Page.query.all()
    content['items'].extend((page.title, url_for('main.show_page', slug=page.slug)) for page in pages)


@sidebar.connect
def sidebar(sender, sidebars):
    add_template_file(sidebars, Path(__file__), 'templates', 'sidebar.html')


@restore.connect
def restore(sender, data, directory, **kwargs):
    if 'page' in data:
        pages = data['page']
        for page in pages:
            p = Page(title=page['title'], slug=page['slug'], body=page['body'],
                     timestamp=datetime.utcfromtimestamp(page['timestamp']), status=Status.published(),
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
