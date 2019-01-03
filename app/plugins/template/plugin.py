import json

from flask import flash, jsonify, redirect
from jinja2 import Template as Jinja2Tempalte

from app.plugins import current_plugin
from .models import Template
from ..models import Plugin
from ...models import Signal
from ...models import db


def get_widget(template):
    all_templates = Template.query.all()
    return {
        'slug': 'template',
        'name': '模板',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', all_templates=all_templates, template=template),
        'js': current_plugin.render_template('widget_edit_article', 'widget.js.html')
    }


@Signal.connect('article', 'edit_widget')
def article_edit_widget(article):
    return get_widget(article.template)


@Signal.connect('page', 'edit_widget')
def page_edit_widget(page):
    return get_widget(page.template)


@Signal.connect('article', 'submit_edit_widget')
def article_submit_edit_widget(slug, js_data, article):
    if slug == 'template':
        for item in js_data:
            if item['name'] == 'template-id':
                if item['value'] != '':
                    article.template = Template.query.get(int(item['value']))


@Signal.connect('page', 'submit_edit_widget')
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
    return Signal.send('article', 'admin_article_list_url', params=kwargs)


def admin_page_list_url(**kwargs):
    return Signal.send('page', 'admin_page_list_url', params=kwargs)


@current_plugin.route('admin', '/list', '管理模板')
def list_tags(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Template.query.order_by(Template.name).paginate(page, per_page=Plugin.get_setting_value('items_per_page'), error_out=False)
        the_templates = pagination.items
        templates.append(current_plugin.render_template('list.html', template_instance=current_plugin, templates=the_templates, pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {}, 'url_for': current_plugin.url_for}, admin_article_list_url=admin_article_list_url, admin_page_list_url=admin_page_list_url))
        scripts.append(current_plugin.render_template('list.js.html'))


@current_plugin.route('admin', '/edit', None)
def edit_template(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        template = None
        if id is not None:
            template = Template.query.get(id)
        templates.append(current_plugin.render_template('edit.html', template=template))
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
        meta['override_render'] = True
        templates.append(redirect(current_plugin.url_for('/list')))


@current_plugin.route('admin', '/new', '新建模板')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(current_plugin.url_for('/edit')))


@current_plugin.signal.connect_this('render_template')
def render(template, json_params):
    template = Jinja2Tempalte(template.body)
    params = {json_param[0]: eval(json_param[1]) for json_param in json_params.items()}
    return template.render(**params)


@Signal.connect('article', 'filter')
def article_filter(query, params, Article):
    if 'template' in params and params['template'] != '':
        query['query'] = query['query'].join(Article.template).filter(Template.slug == params['template'])


@Signal.connect('page', 'filter')
def page_filter(query, params, Page):
    if 'template' in params and params['template'] != '':
        query['query'] = query['query'].join(Page.template).filter(Template.slug == params['template'])


@Signal.connect('article', 'modify_article_when_showing')
def modify_article_when_showing(article):
    if article.template is not None:
        template = Jinja2Tempalte(article.template.body)
        params = {json_param[0]: eval(json_param[1]) for json_param in json.loads(article.body).items()}
        article.body_html = template.render(**params)


@Signal.connect('page', 'modify_page_when_showing')
def modify_page_when_showing(page):
    if page.template is not None:
        template = Jinja2Tempalte(page.template.body)
        params = {json_param[0]: eval(json_param[1]) for json_param in json.loads(page.body).items()}
        page.body_html = template.render(**params)


@Signal.connect('article', 'should_compile_markdown_when_body_change')
def article_should_compile_markdown_when_body_change(article):
    return article.template is None
