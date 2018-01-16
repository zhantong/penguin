from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db, models


def from_typecho(db_url, upload_parent_directory_path):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    from .typecho import User, Content, Comment, Meta, Relationship

    for user in session.query(User).filter_by(group='administrator'):
        db.session.add(user.to_user(role=models.Role.admin()))
    db.session.flush()

    for content in session.query(Content).filter_by(type='post'):
        db.session.add(
            content.to_post(post_type=models.PostType.article(), post_status=models.PostStatus.published()))
    db.session.flush()

    for content in session.query(Content).filter_by(type='page'):
        db.session.add(
            content.to_post(post_type=models.PostType.page(), post_status=models.PostStatus.published()))
    db.session.flush()

    for comment in session.query(Comment):
        if comment.authorId == 0:
            user = comment.to_user(role=models.Role.guest())
            db.session.add(user)
            db.session.flush()
        else:
            user = models.User.query.get(comment.authorId)
        db.session.add(comment.to_comment(author=user))
    db.session.flush()

    for content in session.query(Content).filter_by(type='attachment'):
        attachment = content.to_attachment(upload_parent_directory_path=upload_parent_directory_path)
        db.session.add(attachment)
        db.session.flush()
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='category'):
        meta_category = meta.to_meta_category()
        db.session.add(meta_category)
        db.session.flush()
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post_meta = content.to_post_meta(meta_category)
            db.session.add(post_meta)
    db.session.flush()

    for meta in session.query(Meta).filter_by(type='tag'):
        meta_tag = meta.to_meta_tag()
        db.session.add(meta_tag)
        db.session.flush()
        db.session.refresh(meta_tag)
        for content in session.query(Content) \
                .filter(Content.cid == Relationship.cid) \
                .filter(Relationship.mid == meta.mid):
            post_meta = content.to_post_meta(meta_tag)
            db.session.add(post_meta)
    db.session.flush()

    session.close()
    db.session.commit()
