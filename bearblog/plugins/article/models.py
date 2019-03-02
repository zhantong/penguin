from datetime import datetime
from random import randint

from jieba.analyse.analyzer import ChineseAnalyzer

from bearblog.extensions import db
from sqlalchemy.dialects.mysql import LONGTEXT


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
