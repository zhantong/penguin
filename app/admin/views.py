from flask import render_template, request, current_app, flash, redirect, url_for
from flask_login import login_required
from flask_wtf import FlaskForm
from werkzeug.utils import secure_filename
from . import admin
from ..models import Post, db


@admin.before_request
@login_required
def before_request():
    pass


@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/write-post')
def write_post():
    return render_template('admin/write-post.html')


@admin.route('/manage-posts')
def list_posts():
    action = request.args.get('action', 'list', type=str)
    if action == 'list':
        page = request.args.get('page', 1, type=int)
        keyword = request.args.get('keyword', '', type=str)
        pagination = Post.query.filter(Post.title.contains(keyword)).order_by(Post.timestamp.desc()).paginate(
            page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
        posts = pagination.items
        form = FlaskForm()
        return render_template('admin/manage-posts.html', posts=posts, pagination=pagination, keyword=keyword,
                               form=form)


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
        flash('No file part')
        return 'WRONG'

    file = request.files['files[]']
    filename = secure_filename(file.filename)
    print(filename)
    print(request.form)
    return 'OK'
