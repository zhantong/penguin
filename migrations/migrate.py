from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app import db, models


def from_typecho(db_url):
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    from .typecho import User, Content, Comment

    for user in session.query(User).filter_by(group='administrator'):
        db.session.add(user.to_user(role=models.Role.get_admin()))
    db.session.flush()

    for content in session.query(Content).filter_by(type='post'):
        db.session.add(
            content.to_post(post_type=models.PostType.get_article(), post_status=models.PostStatus.get_published()))
    db.session.flush()

    for comment in session.query(Comment):
        if comment.authorId == 0:
            user = comment.to_user(role=models.Role.get_guest())
            db.session.add(user)
            db.session.flush()
            db.session.refresh(user)
        else:
            user = models.User.query.get(comment.authorId)
        db.session.add(comment.to_comment(author=user))
    db.session.flush()
    session.close()
    db.session.commit()
