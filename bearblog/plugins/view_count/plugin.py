from flask import jsonify, current_app

from bearblog.plugins import current_plugin
from .models import ViewCount
from bearblog.models import Signal
from bearblog.extensions import db


@Signal.connect('api_proxy', 'article')
def article_api_proxy(widget, path, request, article):
    if widget == 'viewCount':
        if request.headers['Authorization'] == current_app.config['SECRET_KEY']:
            view_count = ViewCount.query.filter_by(repository_id=article.repository_id).first()
            if view_count is None:
                view_count = ViewCount(repository_id=article.repository_id, count=0)
                db.session.add(view_count)
                db.session.flush()
            view_count.count += 1
            db.session.commit()
            return jsonify({'success': True})


def restore(repository_id, count):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is None:
        view_count = ViewCount(repository_id=repository_id, count=count)
        db.session.add(view_count)
        db.session.flush()


@Signal.connect('restore', 'article')
def article_restore(article, data):
    if 'view_count' in data:
        restore(article.repository_id, data['view_count'])


@Signal.connect('restore', 'page')
def page_restore(page, data):
    if 'view_count' in data:
        restore(page.repository_id, data['view_count'])


def get_rendered_view_count(repository_id):
    view_count = ViewCount.query.filter_by(repository_id=repository_id).first()
    if view_count is not None:
        return current_plugin.render_template('view_count.html', view_count=view_count.count)


def _article_meta(article):
    return get_rendered_view_count(article.repository_id)


@Signal.connect('meta', 'article')
def article_meta(article):
    return _article_meta(article)


@Signal.connect('article_list_item_meta', 'article')
def article_list_item_meta(article):
    view_count = ViewCount.query.filter_by(repository_id=article.repository_id).first()
    if view_count is not None:
        return {
            'name': '阅读量',
            'slug': current_plugin.slug,
            'value': view_count.count
        }


@Signal.connect('to_json', 'article')
def article_to_json(article):
    view_count = ViewCount.query.filter_by(repository_id=article.repository_id).first()
    return 'viewCount', view_count.count if view_count is not None else 0


@Signal.connect('meta', 'page')
def page_meta(page):
    return get_rendered_view_count(page.repository_id)


@Signal.connect('custom_contents_column', 'article')
def article_custom_contents_column():
    def content_func(article):
        return current_plugin.render_template('article_contents_item.html', view_count=ViewCount.query.filter_by(repository_id=article.repository_id).first().count)

    return {
        'title': '阅读',
        'item': {
            'content': content_func,
        }
    }
