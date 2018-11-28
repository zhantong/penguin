from ...models import db
from .models import Template
from flask import current_app, flash, render_template, jsonify, redirect
from jinja2 import Template as Jinja2Tempalte
from ..models import Plugin
from ..article.plugin import article as article_instance

template = Plugin('模板', 'template')
template_instance = template


@template_instance.signal.connect_this('get_widget')
def get_widget(sender, current_template_id, widget, **kwargs):
    all_templates = Template.query.all()
    current_template = Template.query.filter_by(id=current_template_id).first()
    widget['widget'] = {
        'slug': 'template',
        'name': '模板',
        'html': render_template(template_instance.template_path('widget_edit_article', 'widget.html'),
                                all_templates=all_templates, current_template=current_template),
        'js': render_template(template_instance.template_path('widget_edit_article', 'widget.js.html'))
    }


@template_instance.signal.connect_this('set_widget')
def set_widget(sender, js_data, template, **kwargs):
    template['template'] = None
    for item in js_data:
        if item['name'] == 'template-id':
            if item['value'] != '':
                template['template'] = Template.query.get(int(item['value']))


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


@template.route('admin', '/list', '管理模板')
def list_tags(request, templates, scripts, meta, **kwargs):
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            meta['override_render'] = True
            result = delete(request.form['id'])
            templates.append(jsonify(result))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Template.query.order_by(Template.name) \
            .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        the_templates = pagination.items
        custom_columns = []
        template_instance.signal.send_this('custom_list_column', custom_columns=custom_columns)
        templates.append(
            render_template(template_instance.template_path('list.html'), template_instance=template_instance,
                            templates=the_templates,
                            article_instance=article_instance,
                            pagination={'pagination': pagination, 'endpoint': '/list', 'fragment': {},
                                        'url_for': template_instance.url_for}, custom_columns=custom_columns))
        scripts.append(render_template(template_instance.template_path('list.js.html')))


@template.route('admin', '/edit', None)
def edit_template(request, templates, meta, **kwargs):
    if request.method == 'GET':
        id = request.args.get('id', type=int)
        template = None
        if id is not None:
            template = Template.query.get(id)
        templates.append(render_template(template_instance.template_path('edit.html'), template=template))
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
        templates.append(redirect(template_instance.url_for('/list')))


@template.route('admin', '/new', '新建模板')
def new_tag(templates, meta, **kwargs):
    meta['override_render'] = True
    templates.append(redirect(template_instance.url_for('/edit')))


@template_instance.signal.connect_this('render_template')
def render(sender, template, json_params, html, **kwargs):
    template = Jinja2Tempalte(template.body)
    params = {json_param[0]: eval(json_param[1]) for json_param in json_params.items()}
    html['html'] = template.render(**params)


@template_instance.signal.connect_this('filter')
def filter(sender, query, params, join_db=Template, **kwargs):
    if 'template' in params and params['template'] != '':
        query['query'] = query['query'].join(join_db).filter(Template.slug == params['template'])
