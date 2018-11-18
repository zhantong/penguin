from ...models import db
from .models import Attachment
from ...admin import admin
from ...main import main
from flask import request, jsonify, current_app, url_for, send_from_directory, render_template
import os.path
import uuid
from .. import plugin
from datetime import datetime
from ..article import signals as article_signals
from . import signals
import json

from ..models import Plugin

attachment = Plugin('附件', 'attachment')
attachment_instance = attachment


@plugin.route('/attachment/static/<path:filename>')
def attachment_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@main.route('/attachments/<string:filename>')
def show_attachment(filename):
    attachment = Attachment.query.filter_by(filename=filename).first()
    path = attachment.file_path
    return send_from_directory('../' + current_app.config['UPLOAD_FOLDER'], path,
                               as_attachment=True, attachment_filename=attachment.original_filename)


@admin.route('/upload', methods=['POST'])
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
    if '.' not in filename \
            or filename.rsplit('.', 1)[1].lower() not in current_app.config['ALLOWED_UPLOAD_FILE_EXTENSIONS']:
        return jsonify({
            'code': 3,
            'message': '禁止上传的文件类型'
        })
    extension = filename.rsplit('.', 1)[1].lower()
    random_filename = uuid.uuid4().hex + '.' + extension
    abs_file_path = os.path.join(current_app.config['TEMP_FOLDER'], random_filename)
    os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
    file.save(abs_file_path)
    attachment = Attachment.create(abs_file_path, original_filename=filename, file_extension=extension,
                                   mime=file.mimetype)
    db.session.add(attachment)
    db.session.commit()
    meta = json.loads(request.form.get('meta', type=str))
    signals.on_new_attachment.send(attachment=attachment, meta=meta)
    return jsonify({
        'code': 0,
        'message': '上传成功',
        'file_size': attachment.file_size,
        'relative_path': random_filename,
        'delete_url': url_for('.delete_upload', id=attachment.id)
    })


@admin.route('/upload/<int:id>', methods=['DELETE'])
def delete_upload(id):
    attachment = Attachment.query.get(id)
    db.session.delete(attachment)
    db.session.commit()
    return jsonify({
        'code': 0,
        'message': '删除成功'
    })


@signals.restore.connect
def restore(sender, attachments, directory, restored_attachments, attachment_restored, **kwargs):
    for attachment in attachments:
        a = Attachment.create(file_path=os.path.join(directory,
                                                     attachment['file_path'] if attachment['file_path'][0] != '/' else
                                                     attachment['file_path'][1:]),
                              original_filename=attachment['original_filename'],
                              file_extension=attachment['original_filename'].rsplit('.', 1)[1].lower(),
                              mime=attachment['mime'], timestamp=datetime.utcfromtimestamp(attachment['timestamp']))
        db.session.add(a)
        db.session.flush()
        restored_attachments.append(a)
        attachment_restored(attachment, a.filename)


@article_signals.show_edit_article_widget.connect
def show_edit_article_widget(sender, post, widgets, **kwargs):
    widgets.append({
        'slug': 'attachment',
        'name': '附件',
        'html': render_template(attachment_instance.template_path('widget_edit_article', 'widget.html'),
                                post=post),
        'js': render_template(attachment_instance.template_path('widget_edit_article', 'widget.js.html'),
                              post=post)
    })


@signals.get_widget.connect
def get_widget(sender, attachments, meta, widget, **kwargs):
    widget['widget'] = {
        'slug': 'attachment',
        'name': '附件',
        'html': render_template(attachment_instance.template_path('widget_edit_article', 'widget.html'),
                                attachments=attachments),
        'js': render_template(attachment_instance.template_path('widget_edit_article', 'widget.js.html'),
                              meta=meta)
    }
