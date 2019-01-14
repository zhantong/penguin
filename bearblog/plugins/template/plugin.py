import json

from flask import flash, jsonify, redirect, request
from jinja2 import Template as Jinja2Tempalte

from bearblog.plugins import current_plugin, plugin_url_for, plugin_route
from .models import Template
from bearblog.plugins.models import Plugin
from bearblog.models import Signal
from bearblog.extensions import db

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


@Signal.connect('admin_sidebar_item', 'plugins')
def admin_sidebar_item():
    return {
        'name': current_plugin.name,
        'slug': current_plugin.slug,
        'items': [
            {
                'type': 'link',
                'name': '新建模板',
                'url': plugin_url_for('new', _component='admin')
            },
            {
                'type': 'link',
                'name': '管理模板',
                'url': plugin_url_for('list', _component='admin')
            }
        ]
    }


def get_widget(template):
    all_templates = Template.query.all()
    return {
        'slug': 'template',
        'name': '模板',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', all_templates=all_templates, template=template),
        'js': current_plugin.render_template('widget_edit_article', 'widget.js.html')
    }


@Signal.connect('edit_widget', 'article')
def article_edit_widget(article):
    return get_widget(article.template)


@Signal.connect('edit_widget', 'page')
def page_edit_widget(page):
    return get_widget(page.template)


@Signal.connect('submit_edit_widget', 'article')
def article_submit_edit_widget(slug, js_data, article):
    if slug == 'template':
        for item in js_data:
            if item['name'] == 'template-id':
                if item['value'] != '':
                    article.template = Template.query.get(int(item['value']))


@Signal.connect('submit_edit_widget', 'page')
def page_submit_edit_widget(slug, js_data, page):
    if slug == 'template':
        for item in js_data:
            if item['name'] == 'template-id':
                if item['value'] != '':
                    page.template = Template.query.get(int(item['value']))


def delete(template_id):
    template = Template.query.get(template_id)
    template_name = template.name
    db.session.delete(template)
    db.session.commit()
    message = '已删除模板"' + template_name + '"'
    flash(message)
    return {
        'result': 'OK'
    }


def admin_article_list_url(**kwargs):
    return Signal.send('admin_article_list_url', 'article', params=kwargs)


def admin_page_list_url(**kwargs):
    return Signal.send('admin_page_list_url', 'page', params=kwargs)


@plugin_route('/list', 'list', _component='admin')
def list_tags():
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            result = delete(request.form['id'])
            return jsonify(result)
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Template.query.order_by(Template.name).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        the_templates = pagination.items
        return current_plugin.render_template('list.html', url_for=plugin_url_for, templates=the_templates, pagination={'pagination': pagination, 'fragment': {}, 'url_for': plugin_url_for, 'url_for_params': {'args': ['list'], 'kwargs': {'_component': 'admin'}}}, admin_article_list_url=admin_article_list_url, admin_page_list_url=admin_page_list_url)


@plugin_route('/edit', 'edit', _component='admin')
def edit_template():
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        template = None
        if id is not None:
            template = Template.query.get(id)
        return current_plugin.render_template('edit.html', template=template)
    else:
        id = request.form.get('id', type=int)
        if id is None:
            template = Template()
        else:
            template = Template.query.get(id)
        template.name = request.form['name']
        template.slug = request.form['slug']
        template.description = request.form['description']
        template.body = request.form['body']
        if template.id is None:
            db.session.add(template)
        db.session.commit()
        return redirect(plugin_url_for('list', _component='admin'))


@plugin_route('/new', 'new', _component='admin')
def new_tag():
    return redirect(plugin_url_for('edit', _component='admin'))


@Signal.connect('render_template')
def render(template, json_params):
    template = Jinja2Tempalte(template.body)
    params = {json_param[0]: eval(json_param[1]) for json_param in json_params.items()}
    return template.render(**params)


@Signal.connect('filter', 'article')
def article_filter(query, params, Article):
    if 'template' in params and params['template'] != '':
        query['query'] = query['query'].join(Article.template).filter(Template.slug == params['template'])


@Signal.connect('filter', 'page')
def page_filter(query, params, Page):
    if 'template' in params and params['template'] != '':
        query['query'] = query['query'].join(Page.template).filter(Template.slug == params['template'])


@Signal.connect('modify_article_when_showing', 'article')
def modify_article_when_showing(article):
    if article.template is not None:
        template = Jinja2Tempalte(article.template.body)
        params = {json_param[0]: eval(json_param[1]) for json_param in json.loads(article.body).items()}
        article.body_html = template.render(**params)


@Signal.connect('modify_page_when_showing', 'page')
def modify_page_when_showing(page):
    if page.template is not None:
        template = Jinja2Tempalte(page.template.body)
        params = {json_param[0]: eval(json_param[1]) for json_param in json.loads(page.body).items()}
        page.body_html = template.render(**params)


@Signal.connect('should_compile_markdown_when_body_change', 'article')
def article_should_compile_markdown_when_body_change(article):
    return article.template is None
