from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from ... import db
from flask import url_for


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)

    @staticmethod
    def create(id=None, name=None, slug=None, description=None):
        filter_kwargs = {}
        for param in ['id', 'name', 'slug', 'description']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        return Category(**filter_kwargs)

    def get_info(self):
        return {
            'name': self.name,
            'url': url_for('.index', category=self.slug)
        }
