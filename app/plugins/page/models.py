from ... import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from ...utils import slugify
from ...models import User
from sqlalchemy import Table, Column, Integer, ForeignKey
from random import randint
from ..models import Plugin


def random_number():
    the_min = 100000
    the_max = 999999
    rand = randint(the_min, the_max)

    while Page.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


page_attachment_association_table = Table('page_attachment_association', db.Model.metadata, Column('page_id', Integer, ForeignKey('pages.id')), Column('attachment_id', Integer, ForeignKey('attachments.id')))


class Page(db.Model):
    __tablename__ = 'pages'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, default=random_number, unique=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship(User, backref='pages')
    attachments = db.relationship('Attachment', secondary=page_attachment_association_table, backref='pages')
    repository_id = db.Column(db.String)
    status = db.Column(db.String(200), default='')
    version_remark = db.Column(db.String(), default='')
    version_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, slug):
        self._slug = slugify(slug)

    @staticmethod
    def query_published():
        return Page.query.filter_by(status='published')
