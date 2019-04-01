from sqlalchemy import desc
from flask import Response
from bearblog import component_route
from .models import Comment
from bearblog.extensions import db


def get_comment_to(comment):
    if comment.article is not None:
        return comment.article.to_json()
    if comment.page is not None:
        return comment.page.to_json()


@component_route('/latestComments', 'latest_comments', 'api')
def latest_comments():
    comments = Comment.query.order_by(Comment.timestamp.desc()).limit(10).all()
    return {
        'slug': 'latest_comments',
        'name': '最近回复',
        'comments': [
            {'id': comment.id, 'body': comment.body, 'body_html': comment.body_html, 'timestamp': comment.timestamp,
             'author': comment.author.to_json(), 'to': get_comment_to(comment)} for comment in comments]
    }


@component_route('/admin/comments', 'get_comments', 'api')
def get_comments():
    return {
        'value': [comment.to_json('admin_full') for comment in Comment.query.order_by(desc(Comment.timestamp)).all()]
    }


@component_route('/admin/comment/<int:id>', 'delete_comment', 'api', methods=['DELETE'])
def delete_comment(id):
    comment = Comment.query.get(int(id))
    db.session.delete(comment)
    db.session.commit()
    return Response(status=200)
