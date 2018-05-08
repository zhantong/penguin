from ... import db
from datetime import datetime


class CommentToMail(db.Model):
    __tablename__ = 'comment_to_mail'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    log = db.Column(db.Text)
    comment = db.relationship('Comment', backref='comment_to_mail')
