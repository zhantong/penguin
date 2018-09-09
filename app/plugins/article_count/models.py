from ... import db
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref


class ArticleCount(db.Model):
    __tablename__ = 'article_counts'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, ForeignKey('articles.id'))
    article = relationship('Article', backref=backref('article_count', uselist=False))
    view_count = db.Column(db.Integer, default=0)
