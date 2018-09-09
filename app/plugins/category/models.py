from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ... import db

association_table = Table('article_category_association', db.Model.metadata,
                          Column('article_id', Integer, ForeignKey('articles.id')),
                          Column('category_id', Integer, ForeignKey('categories.id'))
                          )


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    articles = relationship("Article", secondary=lambda: association_table, backref='categories')

    @staticmethod
    def create(id=None, name=None, slug=None, description=None):
        filter_kwargs = {}
        for param in ['id', 'name', 'slug', 'description']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return Category(**filter_kwargs)
