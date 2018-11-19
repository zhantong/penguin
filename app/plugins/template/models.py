from ... import db
from flask import url_for


class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    slug = db.Column(db.String(200))
    description = db.Column(db.Text)
    body = db.Column(db.Text)

    def get_info(self):
        return {
            'name': self.name,
            'url': url_for('.index', template=self.slug),
            'url_params': {
                'template': self.slug
            }
        }
