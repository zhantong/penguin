from bearblog.extensions import db


class Toc(db.Model):
    __tablename__ = 'toc'
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    toc_html = db.Column(db.Text)
    article = db.relationship('Article', backref=db.backref('toc', uselist=False, cascade="all, delete-orphan"))
