from datetime import datetime

import markdown2

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
        target.body_html = markdown2.markdown(value)

    def to_json(self):
        return {
            'id': self.id,
            'body': self.body,
            'bodyHtml': self.body_html,
            'timestamp': self.timestamp,
            'author': self.author.to_json()
        }


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
