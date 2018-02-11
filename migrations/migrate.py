from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db
from app.models import Role as PenguinRole, User as PenguinUser
from app.plugins.post.models import Post as PenguinPost, PostType as PenguinPostType, PostStatus as PenguinPostStatus


def from_typecho(db_url, upload_parent_directory_path):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    from .typecho import User, Content, Comment, Meta, Relationship

    for user in session.query(User).filter_by(group='administrator'):
        db.session.add(user.to_user(role=PenguinRole.admin()))
    db.session.flush()

    for content in session.query(Content).filter_by(type='post'):
        db.session.add(
            content.to_post(post_type=PenguinPostType.article(), post_status=PenguinPostStatus.published()))
    db.session.flush()

    for content in session.query(Content).filter_by(type='page'):
        db.session.add(
            content.to_post(post_type=PenguinPostType.page(), post_status=PenguinPostStatus.published()))
    db.session.flush()

    for comment in session.query(Comment):
        if comment.authorId == 0:
            user = comment.to_user(role=PenguinRole.guest())
            db.session.add(user)
            db.session.flush()
        else:
            user = PenguinUser.query.get(comment.authorId)
        db.session.add(comment.to_comment(author=user))
    db.session.flush()

    for content in session.query(Content).filter_by(type='attachment'):
        attachment = content.to_attachment(upload_parent_directory_path=upload_parent_directory_path)
        db.session.add(attachment)
        db.session.flush()
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='category'):
        category = meta.to_category()
        db.session.add(category)
        db.session.flush()
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post = PenguinPost.query.get(content.cid)
            post.categories.append(category)
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='tag'):
        tag = meta.to_tag()
        db.session.add(tag)
        db.session.flush()
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post = PenguinPost.query.get(content.cid)
            if post is None:
                print(post, content, content.cid)
            post.tags.append(tag)
    db.session.flush()

    session.close()
    db.session.commit()
