from flask import url_for
from sqlalchemy import Table, Column, Integer, ForeignKey

from ... import db

association_table = Table('tag_article_association', db.Model.metadata,
                          Column('tag_id', Integer, ForeignKey('tags.id')),
                          Column('article_id', Integer, ForeignKey('articles.id'))
                          )


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)

    articles = db.relationship('Article', secondary=association_table, backref='tags')

    @staticmethod
    def create(id=None, name=None, slug=None, description=None):
        filter_kwargs = {}
        for param in ['id', 'name', 'slug', 'description']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return Tag(**filter_kwargs)

    def get_info(self):
        return {
            'name': self.name,
            'url': url_for('.index', tag=self.slug),
            'url_params': {
                'tag': self.slug
            }
        }
