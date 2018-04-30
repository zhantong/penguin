from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ... import db

association_table = Table('post_category_association', db.Model.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id')),
                          Column('category_id', Integer, ForeignKey('categories.id'))
                          )


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    posts = relationship("Post", secondary=lambda: association_table,
                         backref='categories')

    @staticmethod
    def create(id=None, name=None, slug=None, description=None):
        return Category(id=id, name=name, slug=slug, description=description)
