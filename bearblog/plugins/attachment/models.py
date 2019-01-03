import os.path
import shutil
import uuid
from datetime import datetime

from flask import current_app
from sqlalchemy import Table, Column, Integer, ForeignKey

from ... import db
from ...utils import md5

attachment_article_association_table = Table('attachment_article_association', db.Model.metadata,
                                             Column('attachment_id', Integer, ForeignKey('attachments.id')),
                                             Column('article_id', Integer, ForeignKey('articles.id'))
                                             )
attachment_page_association_table = Table('attachment_page_association', db.Model.metadata,
                                          Column('attachment_id', Integer, ForeignKey('attachments.id')),
                                          Column('page_id', Integer, ForeignKey('pages.id'))
                                          )


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    original_filename = db.Column(db.String(200))
    filename = db.Column(db.String(200), unique=True)
    file_path = db.Column(db.String(200))
    file_extension = db.Column(db.String(32))
    file_size = db.Column(db.Integer)
    mime = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    md5 = db.Column(db.String(32))

    articles = db.relationship('Article', secondary=attachment_article_association_table, backref='attachments')
    pages = db.relationship('Page', secondary=attachment_page_association_table, backref='attachments')

    @staticmethod
    def create(file_path, original_filename, file_extension, id=None, mime=None, timestamp=None):
        random_filename = uuid.uuid4().hex + '.' + file_extension
        if timestamp is not None:
            dt = timestamp
        else:
            dt = datetime.today()
        relative_file_path = os.path.join(str(dt.year), '%02d' % dt.month, random_filename)
        abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        shutil.copy(file_path, abs_file_path)
        filter_kwargs = {}
        for param in ['id', 'mime', 'timestamp']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return Attachment(original_filename=original_filename, filename=random_filename, file_path=relative_file_path, file_extension=file_extension, **filter_kwargs)

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
