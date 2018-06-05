from ... import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref


class ArticleCount(db.Model):
    __tablename__ = 'article_counts'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, ForeignKey('posts.id'))
    post = relationship('Post', backref=backref('article_count', uselist=False))
    view_count = db.Column(db.Integer, default=0)

    @staticmethod
    def create(id=None, post=None, view_count=None):
        filter_kwargs = {}
        for param in ['id', 'post', 'view_count']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return ArticleCount(**filter_kwargs)
