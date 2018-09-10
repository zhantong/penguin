from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ... import db
from flask import url_for

association_table = Table('post_tag_association', db.Model.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id')),
                          Column('tag_id', Integer, ForeignKey('tags.id'))
                          )


class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    posts = relationship("Post", secondary=lambda: association_table,
                         backref='tags')

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
            'url': url_for('.index', category=self.slug)
        }
