from flask import url_for
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import backref

from bearblog.extensions import db

template_article_association_table = Table('template_article_association', db.Model.metadata,
                                           Column('template_id', Integer, ForeignKey('templates.id')),
                                           Column('article_id', Integer, ForeignKey('articles.id'), unique=True)
                                           )
template_page_association_table = Table('template_page_association', db.Model.metadata,
                                        Column('template_id', Integer, ForeignKey('templates.id')),
                                        Column('page_id', Integer, ForeignKey('pages.id'), unique=True)
                                        )


class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    body = db.Column(db.Text)

    articles = db.relationship('Article', secondary=template_article_association_table, backref=backref('template', uselist=False))
    pages = db.relationship('Page', secondary=template_page_association_table, backref=backref('template', uselist=False))

    def get_info(self):
        return {
            'name': self.name,
            'url': url_for('.index', template=self.slug),
            'url_params': {
                'template': self.slug
            }
        }
