from ... import db
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref

association_table = Table('post_template_association', db.Model.metadata,
                          Column('post_id', Integer, ForeignKey('posts.id'), primary_key=True),
                          Column('template_id', Integer, ForeignKey('templates.id'))
                          )


class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    body = db.Column(db.Text)
    posts = relationship('Post', secondary=lambda: association_table,
                         backref=backref('template', uselist=False))


class TemplateField(db.Model):
    __tablename__ = 'template_fields'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    key = db.Column(db.String(200))
    value = db.Column(db.Text)
    post = db.relationship('Post', backref='template_fields')
