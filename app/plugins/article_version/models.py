from ... import db
from datetime import datetime


class ArticleVersion(db.Model):
    __tablename__ = 'article_versions'
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.String, nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'))
    status = db.Column(db.String(200), default='')
    remark = db.Column(db.String(), default='')
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    article = db.relationship('Article', back_populates='article_version')
