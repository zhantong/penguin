from bearblog import component_route
from .models import Comment


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
