from ... import db
from datetime import datetime
from flask import current_app
import os.path
from ...utils import md5
from ..post.models import Post
from sqlalchemy.orm import backref
import uuid
import shutil


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
    def create(file_path, original_filename, file_extension, id=None, mime=None, timestamp=None, post=None):
        random_filename = uuid.uuid4().hex + '.' + file_extension
        relative_file_path = os.path.join(str(datetime.today().year), '%02d' % datetime.today().month, random_filename)
        abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        shutil.move(file_path, abs_file_path)
        return Attachment(id=id, original_filename=original_filename, filename=random_filename,
                          file_path=relative_file_path, file_extension=file_extension, mime=mime, timestamp=timestamp,
                          post=post)

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
