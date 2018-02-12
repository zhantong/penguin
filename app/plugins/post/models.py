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

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


class Post(db.Model):
    __tablename__ = 'posts'
    __searchable__ = ['title', 'body']
    __analyzer__ = ChineseAnalyzer()
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default='')
    _slug = db.Column('slug', db.String(200), default='')
    post_type_id = db.Column(db.Integer, db.ForeignKey('post_types.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('post_statuses.id'))
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_type = db.relationship('PostType', back_populates='posts')
    post_status = db.relationship('PostStatus', back_populates='posts')
    author = db.relationship('User', backref='posts')
    post_metas = db.relationship('PostMeta', back_populates='post', lazy='dynamic')
    metas = db.relationship('Meta', back_populates='post', lazy='dynamic')

    @hybrid_property
    def slug(self):
        return self._slug

    @slug.setter
    def slug(self, slug):
        self._slug = slugify(slug)

    def __init__(self, **kwargs):
        super(Post, self).__init__(**kwargs)
        if self.post_type is None:
            self.post_type = PostType.query.filter_by(default=True).first()
        if self.post_status is None:
            self.post_status = PostStatus.query.filter_by(default=True).first()
        if self.author is None:
            self.author = current_user._get_current_object()

    @staticmethod
    def create_article(**kwargs):
        return Post(post_type=PostType.article(), **kwargs)

    @staticmethod
    def create_page(**kwargs):
        return Post(post_type=PostType.page(), **kwargs)

    @staticmethod
    def query_articles():
        return Post.query.filter_by(post_type=PostType.article())

    @staticmethod
    def query_pages():
        return Post.query.filter_by(post_type=PostType.page())

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
        if self.post_type == PostType.article():
            return url_for('main.show_article', slug=self.slug)
        if self.post_type == PostType.page():
            return url_for('main.show_page', slug=self.slug)

    def keywords(self):
        keywords = []
        signals.post_keywords.send(post=self, keywords=keywords)
        return keywords


db.event.listen(Post.body, 'set', Post.on_changed_body)


class PostType(db.Model):
    __tablename__ = 'post_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    posts = db.relationship('Post', back_populates='post_type', lazy='dynamic')

    @staticmethod
    def insert_post_types():
        post_types = ('文章', '页面')
        default_post_type = '文章'
        for t in post_types:
            post_type = PostType.query.filter_by(name=t).first()
            if post_type is None:
                post_type = PostType(name=t)
            post_type.default = (post_type.name == default_post_type)
            db.session.add(post_type)
        db.session.commit()

    @staticmethod
    def article():
        return PostType.query.filter_by(name='文章').first()

    @staticmethod
    def page():
        return PostType.query.filter_by(name='页面').first()


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


class Meta(db.Model):
    __tablename__ = 'metas'
    id = db.Column(db.Integer, primary_key=True)
    _key = db.Column('key', db.String(200), default='')
    value = db.Column(db.Text, default='')
    type = db.Column(db.String(200))
    description = db.Column(db.Text, default='')
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    post = db.relationship('Post', back_populates='metas')
    post_metas = db.relationship('PostMeta', back_populates='meta', lazy='dynamic', cascade='all, delete-orphan')

    @hybrid_property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = slugify(key)


class PostMeta(db.Model):
    __tablename__ = 'post_metas'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    key = db.Column(db.String(200))
    value = db.Column(db.String(400))
    description = db.Column(db.Text)
    meta_id = db.Column(db.Integer, db.ForeignKey('metas.id'))
    order = db.Column(db.Integer, default=0)
    post = db.relationship('Post', back_populates='post_metas')
    meta = db.relationship('Meta', back_populates='post_metas')