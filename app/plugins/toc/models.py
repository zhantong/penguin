from ... import db
from ..post.models import Post
import markdown2


class Toc(db.Model):
    __tablename__ = 'toc'
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), primary_key=True)
    toc_html = db.Column(db.Text)
    post = db.relationship('Post', backref=db.backref('toc', uselist=False, cascade="all, delete-orphan"))

    @staticmethod
    def on_changed_post_body(target, value, oldvalue, initiator):
        markdown_html = markdown2.markdown(value, extras=['toc'])
        target.body_html = markdown_html
        target.toc = Toc(toc_html=markdown_html.toc_html)


db.event.listen(Post.body, 'set', Toc.on_changed_post_body)
