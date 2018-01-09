from . import db, login_manager
from datetime import datetime
import markdown2
import re
from flask_login import UserMixin
from flask import url_for
import os.path
from .utils import md5

RE_HTML_TAGS = re.compile(r'<[^<]+?>')


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = ('管理员', '访客')
        default_role = '访客'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    @staticmethod
    def get_admin():
        return Role.query.filter_by(name='管理员').first()

    @staticmethod
    def get_guest():
        return Role.query.filter_by(name='访客').first()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    name = db.Column(db.String(64))
    email = db.Column(db.String(64))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), default='')
    slug = db.Column(db.String(200))
    type_id = db.Column(db.Integer, db.ForeignKey('post_types.id'))
    status_id = db.Column(db.Integer, db.ForeignKey('post_statuses.id'))
    body = db.Column(db.Text, default='')
    body_html = db.Column(db.Text)
    body_abstract = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    attachments = db.relationship('Attachment', backref='attachment', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Post, self).__init__(**kwargs)
        if self.post_type is None:
            self.post_type = PostType.query.filter_by(default=True).first()
        if self.post_status is None:
            self.post_status = PostStatus.query.filter_by(default=True).first()

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        target.body_html = markdown2.markdown(value)
        target.body_abstract = RE_HTML_TAGS.sub('', target.body_html)[:200] + '...'

    def to_json(self, type='view'):
        json_post = {
            'title': self.title,
            'author': self.author.name,
            'timestamp': self.timestamp,
            'comment_count': self.comments.count()
        }
        if type == 'view':
            json_post.update({
                'url': url_for('main.show_post', slug=self.slug)
            })
        elif type == 'admin':
            json_post.update({
                'url': url_for('admin.write_post', id=self.id)
            })
        elif type == 'api':
            pass
        return json_post


db.event.listen(Post.body, 'set', Post.on_changed_body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    ip = db.Column(db.String(64))
    agent = db.Column(db.String(200))
    parent = db.Column(db.Integer)

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        target.body_html = markdown2.markdown(value)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    original_filename = db.Column(db.String(200))
    file_path = db.Column(db.String(200))
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    md5 = db.Column(db.String(32))

    @staticmethod
    def on_change_file_path(target, value, oldvalue, initiator):
        target.file_size = os.path.getsize(value)
        target.md5 = md5(value)


db.event.listen(Attachment.file_path, 'set', Attachment.on_change_file_path)


class PostType(db.Model):
    __tablename__ = 'post_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    posts = db.relationship('Post', backref='post_type', lazy='dynamic')

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
    def get_article():
        return PostType.query.filter_by(name='文章').first()


class PostStatus(db.Model):
    __tablename__ = 'post_statuses'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    posts = db.relationship('Post', backref='post_status', lazy='dynamic')

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
    def get_published():
        return PostStatus.query.filter_by(key='published').first()

    @staticmethod
    def get_draft():
        return PostStatus.query.filter_by(key='draft').first()
