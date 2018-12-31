import json
from .models import ViewCount
from ...models import db
from ..models import Plugin
from ...models import Signal

current_plugin = Plugin.current_plugin()


def viewing(repository_id, request, cookies_to_set):
    view_count_repository_ids = request.cookies.get('view_count_repository_ids')
    if view_count_repository_ids is None:
        view_count_repository_ids = []
    else:
        view_count_repository_ids = json.loads(view_count_repository_ids)
    if repository_id not in view_count_repository_ids:
        view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
        if view_count is None:
            view_count = ViewCount(repository_id=repository_id, count=0)
            db.session.add(view_count)
            db.session.flush()
        view_count.count += 1
        db.session.commit()
        view_count_repository_ids.append(repository_id)
        cookies_to_set['view_count_repository_ids'] = json.dumps(view_count_repository_ids)


@Signal.connect('article', 'on_showing_article')
def on_showing_article(sender, article, request, cookies_to_set, **kwargs):
    viewing(article.repository_id, request, cookies_to_set)


@Signal.connect('page', 'on_showing_page')
def on_showing_article(sender, page, request, cookies_to_set, **kwargs):
    viewing(page.repository_id, request, cookies_to_set)


def restore(repository_id, count):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is None:
        view_count = ViewCount(repository_id=repository_id, count=count)
        db.session.add(view_count)
        db.session.flush()


@Signal.connect('article', 'restore')
def article_restore(sender, article, data, **kwargs):
    if 'view_count' in data:
        restore(article.repository_id, data['view_count'])


@Signal.connect('page', 'restore')
def page_restore(sender, page, data, **kwargs):
    if 'view_count' in data:
        restore(page.repository_id, data['view_count'])


def get_rendered_view_count(repository_id):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is not None:
        return current_plugin.render_template('view_count.html', view_count=view_count.count)


def _article_meta(article):
    return get_rendered_view_count(article.repository_id)


@Signal.connect('article', 'meta')
def article_meta(sender, article, **kwargs):
    return _article_meta(article)


@Signal.connect('article', 'article_list_item_meta')
def article_list_item_meta(sender, article, **kwargs):
    return _article_meta(article)


@Signal.connect('page', 'meta')
def page_meta(sender, page, **kwargs):
    return get_rendered_view_count(page.repository_id)


@Signal.connect('article', 'custom_contents_column')
def article_custom_contents_column(sender, **kwargs):
    def content_func(article):
        return current_plugin.render_template('article_contents_item.html', view_count=ViewCount.query.filter_by(repository_id=article.repository_id).first().count)

    return {
        'title': '阅读',
        'item': {
            'content': content_func,
        }
    }
