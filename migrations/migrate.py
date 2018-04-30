from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db
from app.models import Role as PenguinRole, User as PenguinUser
from app.plugins.post.models import Post as PenguinPost, PostStatus as PenguinPostStatus
from app.plugins.comment.models import Comment as PenguinComment
from app.plugins.attachment.models import Attachment as PenguinAttachment
from app.plugins.category.models import Category as PenguinCategory
from app.plugins.tag.models import Tag as PenguinTag
from datetime import datetime
import phpserialize
import os


def from_typecho(db_url, upload_parent_directory_path):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    from .typecho import User, Content, Comment, Meta, Relationship

    id_to_author = {}
    id_to_post = {}
    id_to_comment = {}

    for user in session.query(User).filter_by(group='administrator'):
        penguin_user = PenguinUser.create(role=PenguinRole.admin(), username=user.name, name=user.screenName,
                                          email=user.mail, member_since=datetime.utcfromtimestamp(user.created))
        id_to_author[user.uid] = penguin_user
        db.session.add(penguin_user)
    db.session.flush()

    for content in session.query(Content).filter_by(type='post'):
        penguin_article = PenguinPost.create()
        penguin_article.update(title=content.title, slug=content.slug, post_type='article',
                               body=content.text.replace('<!--markdown-->', ''),
                               timestamp=datetime.utcfromtimestamp(content.created),
                               post_status=PenguinPostStatus.published(), author=id_to_author[content.authorId])
        id_to_post[content.cid] = penguin_article
        db.session.add(penguin_article)
    db.session.flush()

    for content in session.query(Content).filter_by(type='page'):
        penguin_page = PenguinPost.create()
        penguin_page.update(title=content.title, slug=content.slug, post_type='page',
                            body=content.text.replace('<!--markdown-->', ''),
                            timestamp=datetime.utcfromtimestamp(content.created),
                            post_status=PenguinPostStatus.published(), author=id_to_author[content.authorId])
        id_to_post[content.cid] = penguin_page
        db.session.add(penguin_page)
    db.session.flush()

    for comment in session.query(Comment).order_by(Comment.coid):
        if comment.authorId == 0:
            penguin_user = PenguinUser.create(role=PenguinRole.guest(), name=comment.author,
                                              email=comment.mail,
                                              member_since=datetime.utcfromtimestamp(comment.created))
            db.session.add(penguin_user)
            db.session.flush()
        else:
            penguin_user = id_to_author[comment.authorId]
        penguin_comment = PenguinComment.create(body=comment.text, timestamp=datetime.utcfromtimestamp(comment.created),
                                                ip=comment.ip, agent=comment.agent,
                                                parent=comment.parent if comment.parent == 0 else id_to_comment[
                                                    comment.parent].id,
                                                author=penguin_user, post=id_to_post[comment.cid])
        id_to_comment[comment.coid] = penguin_comment
        db.session.add(penguin_comment)
        db.session.flush()
    db.session.flush()

    for content in session.query(Content).filter_by(type='attachment'):
        meta = {}
        for key, value in phpserialize.loads(bytes(content.text, 'utf-8')).items():
            if type(key) is bytes:
                key = key.decode('utf-8')
            if type(value) is bytes:
                value = value.decode('utf-8')
            meta[key] = value
        file_path = os.path.join(upload_parent_directory_path, meta['path'][1:])
        post = id_to_post[content.parent]
        attachment = PenguinAttachment.create(file_path, content.title, content.title.rsplit('.', 1)[1].lower(),
                                              mime=meta['mime'], timestamp=datetime.utcfromtimestamp(content.created),
                                              post=post)
        db.session.add(attachment)
        db.session.flush()
        post.update(body=post.body.replace(meta['path'], attachment.original_filename))
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='category'):
        category = PenguinCategory.create(name=meta.name, slug=meta.slug, description=meta.description)
        db.session.add(category)
        db.session.flush()
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post = id_to_post[content.cid]
            post.categories.append(category)
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='tag'):
        tag = PenguinTag(name=meta.name, slug=meta.slug, description=meta.description)
        db.session.add(tag)
        db.session.flush()
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post = id_to_post[content.cid]
            post.tags.append(tag)
    db.session.flush()

    session.close()
    db.session.commit()
