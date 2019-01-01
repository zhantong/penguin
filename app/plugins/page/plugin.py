from ..models import Plugin
from ...main import main
from flask import url_for, request, session, make_response, flash, jsonify, send_from_directory, abort
from datetime import datetime
from ...models import db, User
from .models import Page
import json
from uuid import uuid4
from .. import plugin
import os.path
import re
import markdown2
from ...models import Signal

current_plugin = Plugin.current_plugin()


@plugin.route('/page/static/<path:filename>')
def page_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@main.route('/<string:slug>.html')
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
        metas = current_plugin.signal.send_this('meta', page=page)
        widgets = current_plugin.signal.send_this('show_page_widget', session=session, page=page)
        for widget in widgets:
            if widget['slug'] == 'comment':
                after_page_widgets.append(widget)
        current_plugin.signal.send_this('on_showing_page', page=page, request=request, cookies_to_set=cookies_to_set)
        current_plugin.signal.send_this('modify_page_when_showing', page=page)
        resp = make_response(current_plugin.render_template('page.html', page=page, after_page_widgets=after_page_widgets, left_widgets=left_widgets, right_widgets=right_widgets, get_pages=get_pages, metas=metas))
        for key, value in cookies_to_set.items():
            resp.set_cookie(key, value)
        return resp
    else:
        page = None
        dynamic_pages = current_plugin.signal.send_this('dynamic_page')
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


@Signal.connect('app', 'restore')
def restore(data, directory, **kwargs):
    if 'page' in data:
        pages = data['page']
        for page in pages:
            p = Page(title=page['title'], slug=page['slug'], body=page['body'], timestamp=datetime.utcfromtimestamp(page['timestamp']), status=page['version']['status'], repository_id=page['version']['repository_id'], author=User.query.filter_by(username=page['author']).one())
            db.session.add(p)
            db.session.flush()
            current_plugin.signal.send_this('restore', page=p, data=page)


@current_plugin.signal.connect_this('page_url')
def page_url(page, anchor, **kwargs):
    return url_for('main.show_page', slug=page.slug, _anchor=anchor)


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


@current_plugin.route('admin', '/list', '管理页面')
def page_list(request, templates, meta, scripts, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
        else:
            meta['override_render'] = True

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

            templates.append(jsonify({'result': 'OK'}))
    else:
        cleanup_temp_page()
        widget = current_plugin.signal.send_this('get_admin_page_list', params=request.args)
        templates.append(widget['html'])
        scripts.append(widget['js'])


@current_plugin.signal.connect_this('get_admin_page_list')
def get_admin_page_list(params, **kwargs):
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
    return {
        'html': current_plugin.render_template('list.html', repository_ids=repository_ids, pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {}, 'url_for': current_plugin.url_for}, get_pages=get_pages, url_for=current_plugin.url_for),
        'js': current_plugin.render_template('list.js.html')
    }


@current_plugin.route('admin', '/edit', '撰写页面')
def edit_page(request, templates, scripts, csss, **kwargs):
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
        current_plugin.signal.send_this('duplicate', old_page=page, new_page=new_page)
        widgets_dict = json.loads(request.form['widgets'])
        for slug, js_data in widgets_dict.items():
            current_plugin.signal.send_this('submit_edit_widget', slug=slug, js_data=js_data, page=new_page)
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
        widgets.append(current_plugin.signal.send_this('get_widget_submit', page=page))
        widgets.extend(current_plugin.signal.send_this('edit_widget', page=page))
        templates.append(current_plugin.render_template('edit.html', page=page, widgets=widgets))
        scripts.append(current_plugin.render_template('edit.js.html', page=page, widgets=widgets))
        csss.append(current_plugin.render_template('edit.css.html', widgets=widgets))


@current_plugin.signal.connect_this('get_page')
def get_article(page_id, **kwargs):
    return Page.query.get(page_id)


@Signal.connect('main', 'navbar_item')
def navbar_item(**kwargs):
    pages = Page.query.all()
    more = []
    for page in pages:
        more.append({
            'type': 'item',
            'name': page.title,
            'link': url_for('main.show_page', slug=page.slug)
        })
    dynamic_pages = current_plugin.signal.send_this('dynamic_page')
    for page in dynamic_pages:
        more.append({
            'type': 'item',
            'name': page['title'],
            'link': url_for('main.show_page', slug=page['slug'])
        })
    return {
        'more': more
    }


def filter(query, params):
    current_plugin.signal.send_this('filter', query=query, params=params, Page=Page)


@current_plugin.signal.connect_this('get_widget_submit')
def get_widget_submit(page, **kwargs):
    return {
        'slug': 'submit',
        'name': '发布',
        'html': current_plugin.render_template('widget_submit', 'widget.html'),
        'footer': current_plugin.render_template('widget_submit', 'footer.html'),
        'js': current_plugin.render_template('widget_submit', 'widget.js.html', page=page)
    }


@current_plugin.signal.connect_this('admin_page_list_url')
def admin_page_list_url(params, **kwargs):
    return current_plugin.url_for('/list', **params)


RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def on_changed_article_body(target, value, oldvalue, initiator):
    if current_plugin.signal.send_this('should_compile_markdown_when_body_change', page=target):
        html = markdown2.markdown(value)
        target.body_html = html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'


db.event.listen(Page.body, 'set', on_changed_article_body)


@current_plugin.route('admin', '/settings', '设置')
def settings(request, templates, scripts, **kwargs):
    widget = Signal.send('settings', 'get_widget_list', category=current_plugin.slug, meta={'plugin': current_plugin.slug})
    templates.append(widget['html'])
    scripts.append(widget['script'])
