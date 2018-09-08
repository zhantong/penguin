from ... import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from ...utils import slugify
import markdown2
import re
from ...models import User

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


class Status(db.Model):
    __tablename__ = 'page_statuses'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    pages = db.relationship('Page', back_populates='status', lazy='dynamic')

    @staticmethod
    def insert_statuses():
        statuses = (('已发布', 'published'), ('草稿', 'draft'))
        default_status_key = 'draft'
        for name, key in statuses:
            status = Status.query.filter_by(key=key).first()
            if status is None:
                status = Status(key=key, name=name)
            status.default = (status.key == default_status_key)
            db.session.add(status)
        db.session.commit()

    @staticmethod
    def published():
        return Status.query.filter_by(key='published').first()

    @staticmethod
    def draft():
        return Status.query.filter_by(key='draft').first()


class Page(db.Model):
    __tablename__ = 'pages'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    status_id = db.Column(db.Integer, db.ForeignKey('page_statuses.id'))
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.relationship(Status, back_populates='pages')
    author = db.relationship(User, backref='pages')

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, slug):
        self._slug = slugify(slug)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value)
        target.body_html = markdown_html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'


db.event.listen(Page.body, 'set', Page.on_changed_body)
