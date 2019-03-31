from datetime import datetime, timezone
from random import randint

from jieba.analyse.analyzer import ChineseAnalyzer

from bearblog.extensions import db
from bearblog.plugins import current_plugin
from sqlalchemy.dialects.mysql import LONGTEXT
from bearblog.models import Signal

Signal = Signal(None)
Signal.set_default_scope(current_plugin.slug)


def random_number():
    the_min = 100000
    the_max = 999999
    rand = randint(the_min, the_max)

    while Article.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


class Article(db.Model):
    __tablename__ = 'articles'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, default=random_number, unique=True)
    title = db.Column(db.String(200), default='')
    body = db.Column(LONGTEXT, default='')
    body_html = db.Column(LONGTEXT)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', backref='articles')
    repository_id = db.Column(db.String(36))
    status = db.Column(db.String(200), default='')
    version_remark = db.Column(db.TEXT, default='')
    version_timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    @staticmethod
    def query_published():
        return Article.query.filter_by(status='published')

    def to_json(self, level='brief'):
        json = {
            'id': self.id,
            'number': self.number,
            'title': self.title,
            'timestamp': self.timestamp.replace(tzinfo=timezone.utc).isoformat(),
            'author': self.author.to_json(level)
        }
        json['plugin'] = Signal.send('to_json', article=self, level=level)
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
