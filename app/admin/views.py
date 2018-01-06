from flask import render_template

from . import admin


@admin.route('/')
def index():
    return render_template('admin/index.html')


@admin.route('/write-post')
def write_post():
    return render_template('admin/write-post.html')
