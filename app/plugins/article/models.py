from ... import db
from jieba.analyse.analyzer import ChineseAnalyzer
from random import randint
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from ...utils import slugify
import markdown2
import re
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import backref

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def random_number():
    the_min = 1
    the_max = 10000
    rand = randint(the_min, the_max)

    while Article.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


class Status(db.Model):
    __tablename__ = 'article_statuses'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    articles = db.relationship('Article', back_populates='status', lazy='dynamic')

    @staticmethod
    def insert_statuses():
        statuses = (('已发布', 'published'), ('草稿', 'draft'))
        default_post_status_key = 'draft'
        for name, key in statuses:
            status = Status.query.filter_by(key=key).first()
            if status is None:
                status = Status(key=key, name=name)
            status.default = (status.key == default_post_status_key)
            db.session.add(status)
        db.session.commit()

    @staticmethod
    def published():
        return Status.query.filter_by(key='published').first()

    @staticmethod
    def draft():
        return Status.query.filter_by(key='draft').first()


association_table = Table('article_comment_association', db.Model.metadata,
                          Column('article_id', Integer, ForeignKey('articles.id')),
                          Column('comment_id', Integer, ForeignKey('comments.id'), unique=True)
                          )


class Article(db.Model):
    __tablename__ = 'articles'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, default=random_number, unique=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    status_id = db.Column(db.Integer, db.ForeignKey('article_statuses.id'))
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.relationship(Status, back_populates='articles')
    author = db.relationship('User', backref='articles')
    comments = db.relationship('Comment', secondary=association_table, backref=backref('article', uselist=False))

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


db.event.listen(Article.body, 'set', Article.on_changed_body)
