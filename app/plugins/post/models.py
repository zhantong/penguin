from ... import db
from jieba.analyse.analyzer import ChineseAnalyzer
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property
from ...utils import slugify
from flask_login import current_user
import markdown2
from flask import url_for
import re
from . import signals
from random import randint

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


def random_number():
    the_min = 1
    the_max = 10000
    rand = randint(the_min, the_max)

    while Post.query.filter_by(number=rand).first() is not None:
        rand = randint(the_min, the_max)
    return rand


class Post(db.Model):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, default=random_number, unique=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    post_type = db.Column(db.String(40), default='')
    status_id = db.Column(db.Integer, db.ForeignKey('post_statuses.id'))
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_status = db.relationship('PostStatus', back_populates='posts')
    author = db.relationship('User', backref='posts')

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, slug):
        self._slug = slugify(slug)

    def __init__(self, **kwargs):
        super(Post, self).__init__(**kwargs)
        if self.post_type is None:
            self.post_type = 'article'
        if self.post_status is None:
            self.post_status = PostStatus.query.filter_by(default=True).first()
        if self.author is None:
            self.author = current_user._get_current_object()

    @staticmethod
    def create(args=None):
        post = Post()
        signals.create_post.send(post=post, args=args)
        return post

    def update(self, title=None, slug=None, post_type=None, body=None, body_html=None, body_abstract=None,
               timestamp=None, post_status=None, author=None, **kwargs):
        if title is not None:
            self.title = title
        if slug is not None:
            self.slug = slug
        if post_type is not None:
            self.post_type = post_type
        if body is not None:
            self.body = body
        if body_html is not None:
            self.body_html = body_html
        if body_abstract is not None:
            self.body_abstract = body_abstract
        if timestamp is not None:
            self.timestamp = timestamp
        if post_status is not None:
            self.post_status = post_status
        if author is not None:
            self.author = author
        signals.update_post.send(post=self, **kwargs)

    @staticmethod
    def create_article(**kwargs):
        return Post(post_type='article', **kwargs)

    @staticmethod
    def create_page(**kwargs):
        return Post(post_type='page', **kwargs)

    @staticmethod
    def query_articles():
        return Post.query.filter_by(post_type='article')

    @staticmethod
    def query_pages():
        return Post.query.filter_by(post_type='page')

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value)
        target.body_html = markdown_html
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'

    def set_post_status_draft(self):
        self.post_status = PostStatus.draft()

    def set_post_status_published(self):
        self.post_status = PostStatus.published()

    def url(self):
        if self.post_type == 'article':
            return url_for('main.show_article', slug=self.slug)
        if self.post_type == 'page':
            return url_for('main.show_page', slug=self.slug)

    def keywords(self):
        keywords = []
        signals.post_keywords.send(post=self, keywords=keywords)
        return keywords


db.event.listen(Post.body, 'set', Post.on_changed_body)


class PostStatus(db.Model):
    __tablename__ = 'post_statuses'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    posts = db.relationship('Post', back_populates='post_status', lazy='dynamic')

    @staticmethod
    def insert_post_statuses():
        post_statuses = (('已发布', 'published'), ('草稿', 'draft'))
        default_post_status_key = 'draft'
        for name, key in post_statuses:
            post_status = PostStatus.query.filter_by(key=key).first()
            if post_status is None:
                post_status = PostStatus(key=key, name=name)
            post_status.default = (post_status.key == default_post_status_key)
            db.session.add(post_status)
        db.session.commit()

    @staticmethod
    def published():
        return PostStatus.query.filter_by(key='published').first()

    @staticmethod
    def draft():
        return PostStatus.query.filter_by(key='draft').first()
