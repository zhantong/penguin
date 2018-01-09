from flask import render_template, request, current_app, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from . import admin
from ..models import Post, Attachment, db, PostStatus
import os.path
import uuid
from datetime import datetime


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/write-post')
def write_post():
    if 'id' in request.args:
        post = Post.query.get(int(request.args['id']))
    else:
        post = Post(author=current_user._get_current_object())
        db.session.add(post)
        db.session.commit()
        db.session.flush(post)
    return render_template('admin/write-post.html', post=post, form=FlaskForm())


@admin.route('/write-post', methods=['POST'])
def submit_post():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action')
        if action in ['save-draft', 'publish']:
            id = request.form['id']
            body = request.form['body']
            timestamp = request.form['timestamp']
            if timestamp == '':
                timestamp = datetime.now()
            else:
                timestamp = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
            post = Post.query.get(int(id))
            post.body = body
            post.timestamp = timestamp
            if action == 'save-draft':
                post.post_status = PostStatus.get_draft()
                db.session.commit()
                return redirect(url_for('.write_post', id=id))
            elif action == 'publish':
                post.post_status = PostStatus.get_published()
                db.session.commit()
                return redirect(url_for('.list_posts'))


@admin.route('/manage-posts')
def list_posts():
    action = request.args.get('action', 'list', type=str)
    if action == 'list':
        page = request.args.get('page', 1, type=int)
        keyword = request.args.get('keyword', '', type=str)
        status = request.args.get('status', 'all', type=str)
        pagination = Post.query \
            .filter(Post.title.contains(keyword)) \
            .filter(status == 'all' or Post.post_status.has(key=status)) \
            .order_by(Post.timestamp.desc()) \
            .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        posts = pagination.items
        form = FlaskForm()
        return render_template('admin/manage-posts.html', posts=posts, pagination=pagination, keyword=keyword,
                               form=form, post_statuses=PostStatus.query.all(), selected_post_status_key=status)


@admin.route('/manage-posts', methods=['POST'])
def manage_posts():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action')
        if action == 'delete':
            ids = request.form.getlist('id')
            ids = [int(id) for id in ids]
            if ids:
                first_post_title = Post.query.filter(Post.id == ids[0]).first().title
                for post in Post.query.filter(Post.id.in_(ids)):
                    db.session.delete(post)
                db.session.commit()
                message = '已删除文章《' + first_post_title + '》'
                if len(ids) > 1:
                    message += '以及剩下的' + str(len(ids) - 1) + '篇文章'
                flash(message)
            return redirect(url_for('.list_posts'))


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
    filename = secure_filename(file.filename)
    if '.' not in filename \
            or filename.rsplit('.', 1)[1].lower() not in current_app.config['ALLOWED_UPLOAD_FILE_EXTENSIONS']:
        return jsonify({
            'code': 3,
            'message': '禁止上传的文件类型'
        })
    filename_without_extension = filename.rsplit('.', 1)[0]
    extension = filename.rsplit('.', 1)[1]
    filename_generated = filename_without_extension + '_' + str(uuid.uuid4()) + '.' + extension
    save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename_generated)
    file.save(save_path)
    attachment = Attachment(original_filename=filename, file_path=save_path, file_type=file.mimetype)
    db.session.add(attachment)
    db.session.commit()
    print(request.form)
    return jsonify({
        'code': 0,
        'message': '上传成功',
        'file_size': attachment.file_size,
        'relative_path': filename
    })
