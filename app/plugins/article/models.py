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


article_category_association_table = Table('article_category_association', db.Model.metadata,
                                           Column('article_id', Integer, ForeignKey('articles.id')),
                                           Column('category_id', Integer, ForeignKey('categories.id'))
                                           )
article_tag_association_table = Table('article_tag_association', db.Model.metadata,
                                      Column('article_id', Integer, ForeignKey('articles.id')),
                                      Column('tag_id', Integer, ForeignKey('tags.id'))
                                      )

article_comment_association_table = Table('article_comment_association', db.Model.metadata,
                                          Column('article_id', Integer, ForeignKey('articles.id')),
                                          Column('comment_id', Integer, ForeignKey('comments.id'), unique=True)
                                          )

article_attachment_association_table = Table('article_attachment_association', db.Model.metadata,
                                             Column('article_id', Integer, ForeignKey('articles.id')),
                                             Column('attachment_id', Integer, ForeignKey('attachments.id'))
                                             )


class Article(db.Model):
    __tablename__ = 'articles'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, default=random_number, unique=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    author = db.relationship('User', backref='articles')
    categories = db.relationship('Category', secondary=article_category_association_table, backref='articles')
    tags = db.relationship("Tag", secondary=article_tag_association_table, backref='articles')
    comments = db.relationship('Comment', secondary=article_comment_association_table,
                               backref=backref('article', uselist=False))
    attachments = db.relationship('Attachment', secondary=article_attachment_association_table, backref='articles')
    versioned_article = db.relationship('VersionedArticle', uselist=False, back_populates='article')

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, slug):
        self._slug = slugify(slug)

    @staticmethod
    def query_published():
        return Article.query.join(VersionedArticle).filter(VersionedArticle.status == 'published')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value)
        target.body_html = markdown_html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'


db.event.listen(Article.body, 'set', Article.on_changed_body)


class VersionedArticle(db.Model):
    __tablename__ = 'versioned_articles'
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.String, nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    status = db.Column(db.String(200), default='')
    remark = db.Column(db.String(), default='')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    article = db.relationship('Article', back_populates='versioned_article')
