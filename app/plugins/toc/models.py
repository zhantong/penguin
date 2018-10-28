from ... import db
import markdown2
from ..article.models import Article


class Toc(db.Model):
    __tablename__ = 'toc'
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), primary_key=True)
    toc_html = db.Column(db.Text)
    article = db.relationship('Article', backref=db.backref('toc', uselist=False, cascade="all, delete-orphan"))

    @staticmethod
    def on_changed_article_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value, extras=['toc', 'fenced-code-blocks', 'tables'])
        target.body_html = markdown_html
        target.toc = Toc(toc_html=markdown_html.toc_html)


db.event.listen(Article.body, 'set', Toc.on_changed_article_body)
