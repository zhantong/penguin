from ... import db
from datetime import datetime
import markdown2


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    ip = db.Column(db.String(64))
    agent = db.Column(db.String(200))
    parent = db.Column(db.Integer)
    author = db.relationship('User', backref='comments')
    post = db.relationship('Post', backref='comments')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        target.body_html = markdown2.markdown(value)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
