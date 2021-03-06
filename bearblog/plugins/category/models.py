from sqlalchemy import Table, Column, Integer, ForeignKey

from bearblog import component_url_for
from bearblog.extensions import db

association_table = Table('category_article_association', db.Model.metadata,
                          Column('category_id', Integer, ForeignKey('categories.id')),
                          Column('article_id', Integer, ForeignKey('articles.id'))
                          )


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)

    articles = db.relationship('Article', secondary=association_table, backref='categories')

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
            'url': component_url_for('index', 'main', category=self.slug),
            'url_params': {
                'category': self.slug
            }
        }

    def to_json(self, level='brief'):
        json = {
            'id': self.id,
            'slug': self.slug,
            'name': self.name
        }
        if level.startswith('admin_'):
            json['countArticle'] = len(self.articles)
            if level == 'admin_brief':
                return json
            json['description'] = self.description
            if level == 'admin_full':
                return json
        else:
            if level == 'brief':
                return json
        return json
