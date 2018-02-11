from ... import db
from datetime import datetime
from flask import current_app
import os.path
from ...utils import md5
from ..post.models import Post
from sqlalchemy.orm import backref


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    original_filename = db.Column(db.String(200))
    filename = db.Column(db.String(200))
    file_path = db.Column(db.String(200))
    file_extension = db.Column(db.String(32))
    file_size = db.Column(db.Integer)
    mime = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    md5 = db.Column(db.String(32))
    post = db.relationship(Post, backref=backref('attachments', lazy='dynamic'))

    @staticmethod
    def on_change_file_path(target, value, oldvalue, initiator):
        abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], value)
        target.file_size = os.path.getsize(abs_file_path)
        target.md5 = md5(abs_file_path)

    @staticmethod
    def after_delete(mapper, connection, target):
        abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], target.file_path)
        os.remove(abs_file_path)


db.event.listen(Attachment.file_path, 'set', Attachment.on_change_file_path)
db.event.listen(Attachment, 'after_delete', Attachment.after_delete)
