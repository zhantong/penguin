from ... import db
from datetime import datetime


class PostVersion(db.Model):
    __tablename__ = 'post_versions'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    version = db.Column(db.String(20))
    remark = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    post = db.relationship('Post', backref='post_versions')
