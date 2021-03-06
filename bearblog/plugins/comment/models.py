from datetime import datetime

import mistune

from bearblog.extensions import db


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip = db.Column(db.String(64))
    agent = db.Column(db.String(200))
    parent = db.Column(db.Integer)
    author = db.relationship('User', backref='comments')

    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'))

    article = db.relationship('Article', backref='comments')
    page = db.relationship('Page', backref='comments')

    @staticmethod
    def create(id=None, body=None, body_html=None, timestamp=None, ip=None, agent=None, parent=None, author=None):
        filter_kwargs = {}
        for param in ['id', 'body', 'body_html', 'timestamp', 'ip', 'agent', 'parent', 'author']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return Comment(**filter_kwargs)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        class Renderer(mistune.Renderer):
            def __init__(self):
                super().__init__()
                self.toc_count = 0

            def header(self, text, level, raw=None):
                rv = '<h%d id="toc-%d">%s</h%d>\n' % (
                    level, self.toc_count, text, level
                )
                self.toc_count += 1
                return rv

        renderer = Renderer()
        markdown = mistune.Markdown(renderer=renderer)
        target.body_html = markdown(value)

    def to_json(self, level='brief'):
        def get_comment_to(comment):
            if comment.article is not None:
                return comment.article.to_json('admin_brief')
            if comment.page is not None:
                return comment.page.to_json('admin_brief')

        json = {
            'id': self.id
        }
        if level.startswith('admin_'):
            json['body'] = self.body
            json['timestamp'] = self.timestamp
            json['author'] = self.author.to_json('admin_brief')
            json['ip'] = self.ip
            json['to'] = get_comment_to(self)
            if level == 'admin_full':
                return json
        else:
            json['body'] = self.body
            json['timestamp'] = self.timestamp
            json['author'] = self.author.to_json('basic')
            if level == 'basic':
                return json


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
