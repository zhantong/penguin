from flask import render_template
from flask_login import login_required
from . import admin


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
def manage_posts():
    return render_template('admin/manage-posts.html')
