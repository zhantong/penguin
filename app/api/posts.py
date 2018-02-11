from flask import jsonify, request, current_app, url_for, abort
from flask_login import current_user
from . import api
from ..plugins.post.models import Post


@api.route('/posts')
def get_posts():
    type = request.args.get('type', 'api', type=str)
    if type == 'admin':
        if not current_user.is_authenticated:
            return abort(401)
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    pagination = Post.query.filter(Post.title.contains(search)).paginate(
        page, per_page=current_app.config['PENGUIN_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page - 1)
    else:
        prev = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page + 1)
    else:
        next = None
    return jsonify({
        'posts': [post.to_json(type) for post in posts],
        'prev': prev,
        'next': next,
        'total_post': pagination.total
    })
