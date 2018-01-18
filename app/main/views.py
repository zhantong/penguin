from flask import render_template, request, current_app, send_from_directory
from . import main
from ..models import Post, Comment, Attachment
from ..utils import format_comments
from jinja2 import Template


@main.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query_articles().order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'], error_out=False)
    posts = pagination.items
    return render_template('index.html', posts=posts, pagination=pagination)


@main.route('/archives/')
def show_none_post():
    pass


@main.route('/<string:slug>.html', endpoint='show_post_page')
@main.route('/archives/<string:slug>.html')
def show_post(slug):
    post = Post.query.filter_by(slug=slug).first_or_404()
    comments = Comment.query.filter_by(post=post).order_by(Comment.timestamp.desc()).all()
    comments = format_comments(comments)
    if post.is_template_enabled():
        template = Template(post.template_post_meta.meta.value)
        context = {field.key: eval(field.value) for field in post.field_metas.all()}
        return render_template('post.html', post=post, comments=comments, template=template, **context)
    else:
        return render_template('post.html', post=post, comments=comments)


@main.route('/<string:filename>', endpoint='show_attachment_page')
@main.route('/archives/<string:filename>')
def show_attachment(filename):
    attachment = Attachment.query.filter_by(filename=filename).first()
    path = attachment.file_path
    return send_from_directory('../' + current_app.config['UPLOAD_FOLDER'], path)
