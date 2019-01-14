import json
import os.path
import re
from datetime import datetime
from uuid import uuid4

import markdown2
from flask import request, session, make_response, flash, jsonify, send_from_directory, abort

from bearblog.plugins import current_plugin, plugin_url_for, plugin_route
from .models import Page
from bearblog.plugins.models import Plugin
from bearblog.models import Signal, User
from bearblog.extensions import db
from bearblog import component_url_for, component_route

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@component_route('/page/static/<path:filename>', 'page_static')
def page_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@component_route('/<string:slug>.html', 'show_page', 'main')
def show_page(slug):
    def get_pages(repository_id):
        return Page.query.filter_by(repository_id=repository_id).order_by(Page.timestamp.desc()).all()

    page = Page.query.filter_by(slug=slug).order_by(Page.version_timestamp.desc())
    if 'version' in request.args:
        page = page.filter_by(number=request.args['version'])
    page = page.first()
    if page is not None:
        left_widgets = []
        right_widgets = []
        after_page_widgets = []
        cookies_to_set = {}
        metas = Signal.send('meta', page=page)
        widgets = Signal.send('show_page_widget', session=session, page=page)
        for widget in widgets:
            if widget['slug'] == 'comment':
                after_page_widgets.append(widget)
        Signal.send('on_showing_page', page=page, request=request, cookies_to_set=cookies_to_set)
        Signal.send('modify_page_when_showing', page=page)
        resp = make_response(current_plugin.render_template('page.html', page=page, after_page_widgets=after_page_widgets, left_widgets=left_widgets, right_widgets=right_widgets, get_pages=get_pages, metas=metas))
        for key, value in cookies_to_set.items():
            resp.set_cookie(key, value)
        return resp
    else:
        page = None
        dynamic_pages = Signal.send('dynamic_page')
        for dynamic_page in dynamic_pages:
            if dynamic_page['slug'] == slug:
                page = dynamic_page
                break
        if page is None:
            abort(404)
        left_widgets = []
        right_widgets = []
        scripts = []
        styles = []
        scripts.append(page['script'])
        styles.append(page['style'])
        resp = make_response(current_plugin.render_template('dynamic_page.html', page=page, left_widgets=left_widgets, right_widgets=right_widgets, scripts=scripts, styles=styles))
        return resp


@Signal.connect('admin_sidebar_item', 'plugins')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '设置',
                'url': plugin_url_for('settings', _component='admin')
            },
            {
                'type': 'link',
                'name': '管理页面',
                'url': plugin_url_for('list', _component='admin')
            },
            {
                'type': 'link',
                'name': '撰写页面',
                'url': plugin_url_for('edit', _component='admin')
            }
        ]
    }


@Signal.connect('restore', 'bearblog')
def restore(data):
    if 'page' in data:
        pages = data['page']
        for page in pages:
            p = Page(title=page['title'], slug=page['slug'], body=page['body'], timestamp=datetime.utcfromtimestamp(page['timestamp']), status=page['version']['status'], repository_id=page['version']['repository_id'], author=User.query.filter_by(username=page['author']).one())
            db.session.add(p)
            db.session.flush()
            Signal.send('restore', page=p, data=page)


@Signal.connect('page_url')
def page_url(page, anchor):
    return component_url_for('show_page', 'main', slug=page.slug, _anchor=anchor)


def delete(page_id):
    page = Page.query.get(page_id)
    page_title = page.title
    db.session.delete(page)
    db.session.commit()
    message = '已删除文章"' + page_title + '"'
    flash(message)
    return {
        'result': 'OK'
    }


def cleanup_temp_page():
    Page.query.filter_by(status='temp').delete()
    db.session.commit()


@plugin_route('/list', 'list', _component='admin')
def page_list():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
        else:
            page_id = request.form['id']
            action = request.form['action']
            page = Page.query.get(page_id)
            if action == 'publish':
                page.status = 'published'
            elif action == 'archive':
                page.status = 'archived'
            elif action == 'draft':
                page.status = 'draft'
            elif action == 'hide':
                page.status = 'hidden'
            db.session.commit()

            return jsonify({'result': 'OK'})
    else:
        cleanup_temp_page()
        return Signal.send('get_admin_page_list', params=request.args)


@Signal.connect('get_admin_page_list')
def get_admin_page_list(params):
    def get_pages(repository_id):
        return Page.query.filter_by(repository_id=repository_id).order_by(Page.version_timestamp.desc()).all()

    page = 1
    if 'page' in params:
        page = int(params['page'])
    query = db.session.query(Page.repository_id).group_by(Page.repository_id).order_by(Page.version_timestamp.desc())
    query = {'query': query}
    filter(query, params=request.args)
    query = query['query']
    pagination = query.paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
    repository_ids = [item[0] for item in pagination.items]
    return current_plugin.render_template('list.html', repository_ids=repository_ids, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, get_pages=get_pages, url_for=plugin_url_for)


@plugin_route('/edit', 'edit', _component='admin')
def edit_page():
    if request.method == 'POST':
        title = request.form['title']
        slug = request.form['slug']
        body = request.form['body']
        timestamp = datetime.utcfromtimestamp(int(request.form['timestamp']))
        page = Page.query.get(int(request.form['id']))
        if page.repository_id is None:
            repository_id = str(uuid4())
        else:
            repository_id = page.repository_id
        new_page = Page(title=title, slug=slug, body=body, timestamp=timestamp, author=page.author, repository_id=repository_id, status='published')
        Signal.send('duplicate', old_page=page, new_page=new_page)
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            Signal.send('submit_edit_widget', slug=slug, js_data=js_data, page=new_page)
        db.session.add(new_page)
        db.session.commit()
    else:
        cleanup_temp_page()
        if 'id' in request.args:
            page = Page.query.get(int(request.args['id']))
        else:
            page = Page(status='temp')
            db.session.add(page)
            db.session.commit()
        widgets = []
        widgets.append(Signal.send('get_widget_submit', page=page))
        widgets.extend(Signal.send('edit_widget', page=page))
        return current_plugin.render_template('edit.html', page=page, widgets=widgets)


@Signal.connect('get_page')
def get_article(page_id):
    return Page.query.get(page_id)


@Signal.connect('navbar_item', 'main')
def navbar_item():
    pages = Page.query.all()
    more = []
    for page in pages:
        more.append({
            'type': 'item',
            'name': page.title,
            'link': component_url_for('show_page', 'main', slug=page.slug)
        })
    dynamic_pages = Signal.send('dynamic_page')
    for page in dynamic_pages:
        more.append({
            'type': 'item',
            'name': page['title'],
            'link': component_url_for('show_page', 'main', slug=page['slug'])
        })
    return {
        'more': more
    }


def filter(query, params):
    Signal.send('filter', query=query, params=params, Page=Page)


@Signal.connect('get_widget_submit')
def get_widget_submit(page):
    return {
        'slug': 'submit',
        'name': '发布',
        'html': current_plugin.render_template('widget_submit', 'widget.html'),
        'footer': current_plugin.render_template('widget_submit', 'footer.html'),
        'js': current_plugin.render_template('widget_submit', 'widget.js.html', page=page)
    }


@Signal.connect('admin_page_list_url')
def admin_page_list_url(params):
    return plugin_url_for('list', _component='admin', **params)


RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def on_changed_article_body(target, value, oldvalue, initiator):
    if Signal.send('should_compile_markdown_when_body_change', page=target):
        html = markdown2.markdown(value)
        target.body_html = html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'


db.event.listen(Page.body, 'set', on_changed_article_body)


@plugin_route('/settings', 'settings', _component='admin')
def settings():
    return Signal.send('get_rendered_settings', 'settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug})
