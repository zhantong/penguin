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


class OAuth2Token(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False, unique=True)

    token_type = db.Column(db.String(20))
    access_token = db.Column(db.String(48))
    refresh_token = db.Column(db.String(48))
    expires_at = db.Column(db.Integer)
