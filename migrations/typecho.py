from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text
from app import models
from datetime import datetime
import phpserialize
import os.path
import os
import uuid
from flask import current_app
import shutil

Base = declarative_base()


class Comment(Base):
    __tablename__ = 'typecho_comments'
    coid = Column(Integer, primary_key=True)
    cid = Column(Integer, index=True)
    created = Column(Integer, index=True)
    author = Column(String(200))
    authorId = Column(Integer)
    ownerId = Column(Integer)
    mail = Column(String(200))
    url = Column(String(200))
    ip = Column(String(64))
    agent = Column(String(200))
    text = Column(Text)
    type = Column(String(16))
    status = Column(String(16))
    parent = Column(Integer)

    def to_user(self, role):
        return models.User(name=self.author
                           , email=self.mail
                           , member_since=datetime.fromtimestamp(self.created)
                           , role=role
                           )

    def to_comment(self, author):
        return models.Comment(id=self.coid
                              , body=self.text
                              , timestamp=datetime.fromtimestamp(self.created)
                              , author=author
                              , post_id=self.cid
                              , ip=self.ip
                              , agent=self.agent
                              , parent=self.parent
                              )


class Content(Base):
    __tablename__ = 'typecho_contents'
    cid = Column(Integer, primary_key=True)
    title = Column(String(200))
    slug = Column(String(200), index=True)
    created = Column(Integer, index=True)
    modified = Column(Integer, index=True)
    text = Column(Text)
    order = Column(Integer)
    authorId = Column(Integer)
    template = Column(String(32))
    type = Column(String(16))
    status = Column(String(16))
    password = Column(String(32))
    commentsNum = Column(Integer)
    allowComment = Column(String(1))
    allowPing = Column(String(1))
    allowFeed = Column(String(1))
    parent = Column(Integer)
    viewsNum = Column(Integer)

    def to_post(self, post_type, post_status):
        return models.Post(id=self.cid
                           , title=self.title
                           , slug=self.slug
                           , post_type=post_type
                           , post_status=post_status
                           , body=self.text.replace('<!--markdown-->', '')
                           , timestamp=datetime.fromtimestamp(self.created)
                           , author_id=self.authorId
                           )

    def to_attachment(self, upload_parent_directory_path):
        def parse_meta(raw):
            result = {}
            for key, value in phpserialize.loads(bytes(raw, 'utf-8')).items():
                if type(key) is bytes:
                    key = key.decode('utf-8')
                if type(value) is bytes:
                    value = value.decode('utf-8')
                result[key] = value
            return result

        meta = parse_meta(self.text)
        original_filename = self.title
        original_relative_file_path = meta['path']
        original_abs_file_path = os.path.join(upload_parent_directory_path, original_relative_file_path[1:])
        extension = original_filename.rsplit('.', 1)[1].lower()
        filename = uuid.uuid4().hex + '.' + extension
        timestamp = datetime.fromtimestamp(self.created)
        relative_file_path = os.path.join(str(timestamp.year), '%02d' % timestamp.month, filename)
        abs_file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], relative_file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        shutil.copyfile(original_abs_file_path, abs_file_path)
        post = models.Post.query.get(self.parent)
        if post is not None:
            post.body = post.body.replace(original_relative_file_path, filename)
        else:
            print('a attachment (id = ' + str(self.cid) + ') has no corresponding post (id = ' + str(self.parent) + ')')
        return models.Attachment(post_id=self.parent, original_filename=original_filename, filename=filename,
                                 file_path=relative_file_path, file_extension=extension, mime=meta['mime'],
                                 timestamp=timestamp)

    def to_post_meta(self, meta):
        return models.PostMeta(post_id=self.cid, meta=meta)


class Meta(Base):
    __tablename__ = 'typecho_metas'
    mid = Column(Integer, primary_key=True)
    name = Column(String(200))
    slug = Column(String(200))
    type = Column(String(32))
    description = Column(String(200))
    count = Column(Integer)
    order = Column(Integer)
    parent = Column(Integer)

    def to_meta_category(self):
        return models.Meta(key=self.slug, value=self.name, type='category', description=self.description)


class Option(Base):
    __tablename__ = 'typecho_options'
    name = Column(String(32), primary_key=True)
    user = Column(Integer, primary_key=True)
    value = Column(Text)


class Relationship(Base):
    __tablename__ = 'typecho_relationships'
    cid = Column(Integer, primary_key=True)
    mid = Column(Integer, primary_key=True)


class User(Base):
    __tablename__ = 'typecho_users'
    uid = Column(Integer, primary_key=True)
    name = Column(String(32))
    password = Column(String(64))
    mail = Column(String(200))
    url = Column(String(200))
    screenName = Column(String(32))
    created = Column(Integer)
    activated = Column(Integer)
    logged = Column(Integer)
    group = Column(String(16))
    authCode = Column(String(64))

    def to_user(self, role):
        return models.User(id=self.uid
                           , username=self.name
                           , role=role
                           , name=self.screenName
                           , email=self.mail
                           , member_since=datetime.fromtimestamp(self.created)
                           )
