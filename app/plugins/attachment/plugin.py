from blinker import signal
from ...models import db
from .models import Attachment
from ...admin import admin
from ...main import main
from flask import request, jsonify, current_app, url_for, send_from_directory
import os.path
from datetime import datetime
import uuid
from .. import plugin

edit_article = signal('edit_article')
edit_page = signal('edit_page')


@plugin.route('/attachment/static/<path:filename>')
def attachment_static(filename):
    return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)


@main.route('/<string:filename>', endpoint='show_attachment_page')
@main.route('/archives/<string:filename>')
def show_attachment(filename):
    attachment = Attachment.query.filter_by(filename=filename).first()
    path = attachment.file_path
    return send_from_directory('../' + current_app.config['UPLOAD_FOLDER'], path)


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
    post_id = request.form['post_id']
    extension = filename.rsplit('.', 1)[1].lower()
    random_filename = uuid.uuid4().hex + '.' + extension
    relative_file_path = os.path.join(str(datetime.today().year), '%02d' % datetime.today().month, random_filename)
    abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_file_path)
    os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
    file.save(abs_file_path)
    attachment = Attachment(post_id=post_id, original_filename=filename, filename=random_filename
                            , file_path=relative_file_path, file_extension=extension, mime=file.mimetype)
    db.session.add(attachment)
    db.session.commit()
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


@edit_page.connect
@edit_article.connect
def edit_article(sender, args, context, styles, hiddens, contents, widgets, scripts):
    context['attachments'] = Attachment.query.filter_by(post_id=context['post'].id).all()
    widgets.append(os.path.join('attachment', 'templates', 'widget_content_attachment.html'))
    scripts.append(os.path.join('attachment', 'templates', 'widget_script_attachment.html'))
