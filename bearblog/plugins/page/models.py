from datetime import datetime
from random import randint

from sqlalchemy.ext.hybrid import hybrid_property

from bearblog.extensions import db
from bearblog.models import User
from bearblog.utils import slugify
from bearblog.models import Signal
from bearblog.plugins import current_plugin

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


def random_number():
    the_min = 100000
    the_max = 999999
    rand = randint(the_min, the_max)

    while Page.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


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
    repository_id = db.Column(db.String(36))
    status = db.Column(db.String(200), default='')
    version_remark = db.Column(db.TEXT, default='')
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

    def to_json(self, level='basic'):
        json = {
            'id': self.id,
            'number': self.number,
            'title': self.title,
            'timestamp': self.timestamp,
            'author': self.author.to_json()
        }
        json['plugin'] = Signal.send('to_json', page=self, level=level)
        if level.startswith('admin_'):
            json['repositoryId'] = self.repository_id
            json['status'] = self.status
            json['versionTimestamp'] = self.version_timestamp
            if level == 'admin_brief':
                return json
            json['bodyAbstract'] = self.body_abstract
            if level == 'admin_basic':
                return json
            json['body'] = self.body
            if level == 'admin_full':
                return json
        else:
            if level == 'brief':
                return json
            json['bodyAbstract'] = self.body_abstract
            if level == 'basic':
                return json
            json['body'] = self.body
            json['bodyHtml'] = self.body_html
            if level == 'full':
                return json
        if level == 'basic':
            return json
        json['body'] = self.body
        json['bodyHtml'] = self.body_html
        if level == 'full':
            return json
