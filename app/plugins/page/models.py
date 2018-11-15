from ... import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from ...utils import slugify
import markdown2
import re
from ...models import User
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import backref
from random import randint
from ..view_count import signals as view_count_signals

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def random_number():
    the_min = 100000
    the_max = 999999
    rand = randint(the_min, the_max)

    while Page.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


page_comment_association_table = Table('page_comment_association', db.Model.metadata,
                                       Column('page_id', Integer, ForeignKey('pages.id')),
                                       Column('comment_id', Integer, ForeignKey('comments.id'), unique=True)
                                       )

page_attachment_association_table = Table('page_attachment_association', db.Model.metadata,
                                          Column('page_id', Integer, ForeignKey('pages.id')),
                                          Column('attachment_id', Integer, ForeignKey('attachments.id'))
                                          )


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
    comments = db.relationship('Comment', secondary=page_comment_association_table,
                               backref=backref('page', uselist=False))
    attachments = db.relationship('Attachment', secondary=page_attachment_association_table, backref='pages')
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    template = db.relationship('Template', backref='pages')
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

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value)
        target.body_html = markdown_html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'

    def get_view_count(self):
        count = {}
        view_count_signals.get_count.send(repository_id=self.repository_id, count=count)
        return count['count']


db.event.listen(Page.body, 'set', Page.on_changed_body)
