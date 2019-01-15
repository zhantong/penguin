import json
import os.path
import uuid
from datetime import datetime

from flask import request, jsonify, current_app, url_for, send_from_directory

from bearblog.plugins import current_plugin, plugin_route, plugin_url_for
from .models import Attachment
from bearblog.models import Signal
from bearblog.extensions import db
from bearblog import component_route,component_url_for


@Signal.connect('deploy', 'bearblog')
def deploy():
    current_plugin.set_setting('allowed_upload_file_extensions', name='允许上传文件后缀', value='txt pdf png jpg jpeg gif', value_type='str_list')


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
            }
        ]
    }


@plugin_route('/settings', 'settings', _component='admin')
def settings():
    return Signal.send('get_rendered_settings', 'settings', category=current_plugin.slug, meta={'plugin': current_plugin.slug})


@component_route('/attachment/static/<path:filename>', 'attachment_static')
def attachment_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@component_route('/attachments/<string:filename>', 'show_attachment', 'main')
def show_attachment(filename):
    attachment = Attachment.query.filter_by(filename=filename).first()
    path = attachment.file_path
    return send_from_directory('../' + current_app.config['UPLOAD_FOLDER'], path, as_attachment=True, attachment_filename=attachment.original_filename)


@component_route('/upload', 'upload', 'admin', methods=['POST'])
def upload():
    if 'files[]' not in request.files:
        return jsonify({
            'code': 1,
            'message': '上传文件不存在'
        })
    file = request.files['files[]']
    if file.filename == '':
        return jsonify({
            'code': 2,
            'message': '未选择上传文件'
        })
    filename = file.filename
    if '.' not in filename or filename.rsplit('.', 1)[1].lower() not in current_plugin.get_setting_value_this('allowed_upload_file_extensions'):
        return jsonify({
            'code': 3,
            'message': '禁止上传的文件类型'
        })
    extension = filename.rsplit('.', 1)[1].lower()
    random_filename = uuid.uuid4().hex + '.' + extension
    abs_file_path = os.path.join(current_app.config['TEMP_FOLDER'], random_filename)
    os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
    file.save(abs_file_path)
    attachment = Attachment.create(abs_file_path, original_filename=filename, file_extension=extension, mime=file.mimetype)
    db.session.add(attachment)
    db.session.commit()
    meta = json.loads(request.form.get('meta', type=str))
    if 'article_id' in meta:
        article = Signal.send('get_article', 'article', article_id=meta['article_id'])
        article.attachments.append(attachment)
        db.session.commit()
    if 'page_id' in meta:
        page = Signal.send('get_page', 'page', page_id=meta['page_id'])
        page.attachments.append(attachment)
        db.session.commit()
    return jsonify({
        'code': 0,
        'message': '上传成功',
        'file_size': attachment.file_size,
        'relative_path': random_filename,
        'delete_url': component_url_for('.upload_delete', 'admin', id=attachment.id)
    })


@component_route('/upload/<int:id>', 'upload_delete', 'admin', methods=['DELETE'])
def delete_upload(id):
    attachment = Attachment.query.get(id)
    db.session.delete(attachment)
    db.session.commit()
    return jsonify({
        'code': 0,
        'message': '删除成功'
    })


@Signal.connect('restore', 'article')
def article_restore(article, data, directory):
    if 'attachments' in data:
        restored_attachments = []
        for attachment in data['attachments']:
            a = Attachment.create(file_path=os.path.join(directory, attachment['file_path'] if attachment['file_path'][0] != '/' else attachment['file_path'][1:]), original_filename=attachment['original_filename'], file_extension=attachment['original_filename'].rsplit('.', 1)[1].lower(), mime=attachment['mime'], timestamp=datetime.utcfromtimestamp(attachment['timestamp']))
            db.session.add(a)
            db.session.flush()
            restored_attachments.append(a)
            article.body = article.body.replace(attachment['file_path'], '/attachments/' + a.filename)
        article.attachments = restored_attachments


def get_widget(attachments, meta):
    return {
        'slug': 'attachment',
        'name': '附件',
        'html': current_plugin.render_template('widget_edit_article', 'widget.html', attachments=attachments),
        'js': current_plugin.render_template('widget_edit_article', 'widget.js.html', meta=meta)
    }


@Signal.connect('edit_widget', 'article')
def article_edit_widget(article):
    meta = {
        'article_id': article.id
    }
    return get_widget(article.attachments, meta)


@Signal.connect('edit_widget', 'page')
def page_edit_widget(page):
    meta = {
        'page_id': page.id
    }
    return get_widget(page.attachments, meta)


@Signal.connect('duplicate', 'article')
def article_duplicate(old_article, new_article):
    new_article.attachments = old_article.attachments


@Signal.connect('duplicate', 'page')
def page_duplicate(old_page, new_page):
    new_page.attachments = old_page.attachments
