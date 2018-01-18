from flask import render_template, request, current_app, flash, redirect, url_for, jsonify
from flask_login import login_required
from flask_wtf import FlaskForm
from . import admin
from ..models import Post, Attachment, db, PostStatus, Meta, PostMeta, Comment
import os.path
import uuid
from datetime import datetime
from sqlalchemy.orm import load_only
from ..utils import slugify
from sqlalchemy import desc


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/edit-article')
def edit_article():
    if 'id' in request.args:
        post = Post.query.get(int(request.args['id']))
    else:
        post = Post.create_article()
        db.session.add(post)
        db.session.commit()
        db.session.refresh(post)
    attachments = Attachment.query.filter_by(post_id=post.id).all()
    return render_template('admin/edit-article.html', post=post, form=FlaskForm(), attachments=attachments
                           , all_category_metas=Meta.categories()
                           , category_meta_ids=[category_post_meta.meta_id for category_post_meta
                                                in post.category_post_metas.options(load_only('meta_id'))]
                           , all_tag_metas=Meta.tags()
                           , tags=[tag_post_meta.meta.value for tag_post_meta in post.tag_post_metas.all()]
                           , all_template_metas=Meta.templates())


@admin.route('/edit-article', methods=['POST'])
def submit_article():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action')
        if action in ['save-draft', 'publish']:
            id = request.form['id']
            title = request.form['title']
            slug = request.form['slug']
            timestamp = request.form.get('timestamp', type=int)
            category_meta_ids = request.form.getlist('category-id')
            tag_names = request.form.getlist('tag')
            timestamp = datetime.utcfromtimestamp(timestamp)
            post = Post.query.get(int(id))
            post.title = title
            post.slug = slug
            post.timestamp = timestamp
            post.category_post_metas = [PostMeta(post=post, meta_id=category_meta_id)
                                        for category_meta_id in category_meta_ids]
            tag_post_metas = []
            for tag_name in tag_names:
                tag = Meta.query_tags().filter_by(value=tag_name).first()
                if tag is None:
                    tag = Meta.create_tag(key=tag_name, value=tag_name)
                    db.session.add(tag)
                    db.session.flush()
                tag_post_meta = PostMeta(post=post, meta=tag)
                tag_post_metas.append(tag_post_meta)
            post.tag_post_metas = tag_post_metas
            if post.is_template_enabled():
                field_keys = request.form.getlist('field-key')
                field_values = request.form.getlist('field-value')
                post.field_metas = []
                for key, value in zip(field_keys, field_values):
                    post.field_metas.append(Meta.create_field(key=key, value=value))
            else:
                body = request.form['body']
                post.body = body
            if action == 'save-draft':
                post.set_post_status_draft()
                db.session.commit()
                return redirect(url_for('.edit_article', id=id))
            elif action == 'publish':
                post.set_post_status_published()
                db.session.commit()
                return redirect(url_for('.list_articles'))
        elif action == 'enable-template':
            id = request.form['id']
            template_id = request.form['template']
            post = Post.query.get(int(id))
            post.template_post_meta = PostMeta(post=post, meta_id=int(template_id))
            db.session.commit()
            return redirect(url_for('.edit_article', id=id))
        elif action == 'disable-template':
            id = request.form['id']
            post = Post.query.get(int(id))
            post.template_post_meta = None
            db.session.commit()
            return redirect(url_for('.edit_article', id=id))


@admin.route('/manage-articles')
def list_articles():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '', type=str)
    category = request.args.get('category', '', type=str)
    tag = request.args.get('tag', '', type=str)
    template = request.args.get('template', '', type=str)
    status = request.args.get('status', '', type=str)
    query = Post.query_articles().filter(Post.title.contains(keyword))
    if category != '':
        query = query.join(PostMeta, Meta).filter(Meta.key == category and Meta.type == 'category')
    if status != '':
        query = query.filter(Post.post_status.has(key=status))
    if tag != '':
        query = query.join(PostMeta, Meta).filter(Meta.key == tag and Meta.type == 'tag')
    if template != '':
        query = query.join(PostMeta, Meta).filter(Meta.key == template and Meta.type == 'template')
    query = query.order_by(Post.timestamp.desc())
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-articles.html', posts=posts, pagination=pagination, keyword=keyword
                           , category=category, tag=tag, form=form, post_statuses=PostStatus.query.all()
                           , selected_post_status_key=status
                           , category_metas=Meta.query_categories().order_by(Meta.value).all())


@admin.route('/manage-articles', methods=['POST'])
def manage_articles():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action', '', type=str)
        if action == 'delete':
            ids = request.form.getlist('id')
            ids = [int(id) for id in ids]
            if ids:
                first_post_title = Post.query.get(ids[0]).title
                for post in Post.query.filter(Post.id.in_(ids)):
                    db.session.delete(post)
                db.session.commit()
                message = '已删除文章《' + first_post_title + '》'
                if len(ids) > 1:
                    message += '以及剩下的' + str(len(ids) - 1) + '篇文章'
                flash(message)
    return redirect(url_for('.list_articles'))


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


@admin.route('/manage-categories')
def list_categories():
    page = request.args.get('page', 1, type=int)
    pagination = Meta.query_categories().order_by(Meta.value) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    categories = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-categories.html', categories=categories, pagination=pagination, form=form)


@admin.route('/manage-categories', methods=['POST'])
def manage_categories():
    action = request.form.get('action', '', type=str)
    if action == 'delete':
        ids = request.form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_category_name = Meta.query.get(ids[0]).value
            for category in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(category)
            db.session.commit()
            message = '已删除分类"' + first_category_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '种分类'
            flash(message)
    return redirect(url_for('.list_categories'))


@admin.route('/edit-category')
def show_category():
    id = request.args.get('id', type=int)
    if id is None:
        category = Meta()
    else:
        category = Meta.query.get(id)
    return render_template('admin/edit-category.html', category=category)


@admin.route('/edit-category', methods=['POST'])
def manage_category():
    id = request.form.get('id', type=int)
    if id is None:
        category = Meta().create_category()
    else:
        category = Meta.query.get(id)
    category.key = request.form['key']
    category.value = request.form['value']
    category.description = request.form['description']
    if category.id is None:
        db.session.add(category)
    db.session.commit()
    return redirect(url_for('.list_categories'))


@admin.route('/manage-tags')
def list_tags():
    page = request.args.get('page', 1, type=int)
    pagination = Meta.query_tags().order_by(Meta.value) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    tags = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-tags.html', tags=tags, pagination=pagination, form=form)


@admin.route('/manage-tags', methods=['POST'])
def manage_tags():
    action = request.form.get('action', '', type=str)
    if action == 'delete':
        ids = request.form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_tag_name = Meta.query.get(ids[0]).value
            for tag in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(tag)
            db.session.commit()
            message = '已删除标签"' + first_tag_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个标签'
            flash(message)
    return redirect(url_for('.list_tags'))


@admin.route('/edit-tag')
def show_tag():
    id = request.args.get('id', type=int)
    tag = None
    if id is not None:
        tag = Meta.query.get(id)
    return render_template('admin/edit-tag.html', tag=tag)


@admin.route('/edit-tag', methods=['POST'])
def manage_tag():
    id = request.form.get('id', type=int)
    if id is None:
        tag = Meta().create_tag()
    else:
        tag = Meta.query.get(id)
    tag.key = request.form['key']
    tag.value = request.form['value']
    tag.description = request.form['description']
    if tag.id is None:
        db.session.add(tag)
    db.session.commit()
    return redirect(url_for('.list_tags'))


@admin.route('/edit-page')
def edit_page():
    if 'id' in request.args:
        post = Post.query.get(int(request.args['id']))
    else:
        post = Post().create_page()
        db.session.add(post)
        db.session.commit()
    attachments = Attachment.query.filter_by(post=post).all()
    return render_template('admin/edit-page.html', post=post, form=FlaskForm(), attachments=attachments
                           , all_template_metas=Meta.templates())


@admin.route('/edit-page', methods=['POST'])
def submit_page():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action')
        if action in ['save-draft', 'publish']:
            id = request.form['id']
            title = request.form['title']
            slug = request.form['slug']
            timestamp = request.form.get('timestamp', type=int)
            timestamp = datetime.utcfromtimestamp(timestamp)
            post = Post.query.get(int(id))
            post.title = title
            post.slug = slug
            post.timestamp = timestamp
            if post.is_template_enabled():
                field_keys = request.form.getlist('field-key')
                field_values = request.form.getlist('field-value')
                post.field_metas = []
                for key, value in zip(field_keys, field_values):
                    post.field_metas.append(Meta.create_field(key=key, value=value))
            else:
                body = request.form['body']
                post.body = body
            if action == 'save-draft':
                post.set_post_status_draft()
                db.session.commit()
                return redirect(url_for('.edit_page', id=id))
            elif action == 'publish':
                post.set_post_status_published()
                db.session.commit()
                return redirect(url_for('.list_pages'))
        elif action == 'enable-template':
            id = request.form['id']
            template_id = request.form['template']
            post = Post.query.get(int(id))
            post.template_post_meta = PostMeta(post=post, meta_id=int(template_id))
            db.session.commit()
            return redirect(url_for('.edit_page', id=id))
        elif action == 'disable-template':
            id = request.form['id']
            post = Post.query.get(int(id))
            post.template_post_meta = None
            db.session.commit()
            return redirect(url_for('.edit_page', id=id))


@admin.route('/manage-pages')
def list_pages():
    page = request.args.get('page', 1, type=int)
    keyword = request.args.get('keyword', '', type=str)
    status = request.args.get('status', '', type=str)
    query = Post.query_pages().filter(Post.title.contains(keyword))
    if status != '':
        query = query.filter(Post.post_status.has(key=status))
    query = query.order_by(Post.timestamp.desc())
    pagination = query.paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-pages.html', posts=posts, pagination=pagination, keyword=keyword
                           , form=form, post_statuses=PostStatus.query.all()
                           , selected_post_status_key=status)


@admin.route('/manage-pages', methods=['POST'])
def manage_pages():
    form = FlaskForm()
    if form.validate_on_submit():
        action = request.form.get('action', '', type=str)
        if action == 'delete':
            ids = request.form.getlist('id')
            ids = [int(id) for id in ids]
            if ids:
                first_post_title = Post.query.get(ids[0]).title
                for post in Post.query.filter(Post.id.in_(ids)):
                    db.session.delete(post)
                db.session.commit()
                message = '已删除页面《' + first_post_title + '》'
                if len(ids) > 1:
                    message += '以及剩下的' + str(len(ids) - 1) + '个页面'
                flash(message)
    return redirect(url_for('.list_pages'))


@admin.route('/trans-slug')
def trans_slug():
    return jsonify({
        'slug': slugify(request.args['string'])
    })


@admin.route('/manage-templates')
def list_templates():
    page = request.args.get('page', 1, type=int)
    pagination = Meta.query_templates().order_by(Meta.key) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    templates = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-templates.html', templates=templates, pagination=pagination, form=form)


@admin.route('/manage-templates', methods=['POST'])
def manage_templates():
    action = request.form.get('action', '', type=str)
    if action == 'delete':
        ids = request.form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_template_name = Meta.query.get(ids[0]).key
            for template in Meta.query.filter(Meta.id.in_(ids)):
                db.session.delete(template)
            db.session.commit()
            message = '已删除模板"' + first_template_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '个模板'
            flash(message)
    return redirect(url_for('.list_templates'))


@admin.route('/edit-template')
def show_template():
    id = request.args.get('id', type=int)
    template = None
    if id is not None:
        template = Meta.query.get(id)
    return render_template('admin/edit-template.html', template=template)


@admin.route('/edit-template', methods=['POST'])
def manage_template():
    id = request.form.get('id', type=int)
    if id is None:
        template = Meta().create_template()
    else:
        template = Meta.query.get(id)
    template.key = request.form['key']
    template.value = request.form['value']
    template.description = request.form['description']
    if template.id is None:
        db.session.add(template)
    db.session.commit()
    return redirect(url_for('.list_templates'))


@admin.route('/manage-comments')
def list_comments():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(desc(Comment.timestamp)) \
        .paginate(page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    comments = pagination.items
    form = FlaskForm()
    return render_template('admin/manage-comments.html', comments=comments, pagination=pagination, form=form)


@admin.route('/manage-comments', methods=['POST'])
def manage_comments():
    action = request.form.get('action', '', type=str)
    if action == 'delete':
        ids = request.form.getlist('id')
        ids = [int(id) for id in ids]
        if ids:
            first_comment_name = Comment.query.get(ids[0]).body
            for comment in Comment.query.filter(Comment.id.in_(ids)):
                db.session.delete(comment)
            db.session.commit()
            message = '已删除分类"' + first_comment_name + '"'
            if len(ids) > 1:
                message += '以及剩下的' + str(len(ids) - 1) + '条评论'
            flash(message)
    return redirect(url_for('.list_comments'))
