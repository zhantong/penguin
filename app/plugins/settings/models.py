from ... import db
from datetime import datetime


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    slug = db.Column(db.String(100))
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    value_type = db.Column(db.String(40))
    category = db.Column(db.String(40))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_value(slug, category='penguin'):
        item = Settings.query.filter_by(slug=slug, category=category).first()
        if item is not None:
            if item.value_type is None:
                return item.value
            return eval(item.value_type)(item.value)
        return None

    @staticmethod
    def get(slug, category='settings'):
        item = Settings.query.filter_by(slug=slug, category=category).first()
        if item is None:
            return None
        return {
            'raw_value': item.value,
            'value': Settings.get_value(slug, category),
            'description': item.description,
            'value_type': item.value_type
        }

    @staticmethod
    def set(slug, category='settings', **kwargs):
        item = Settings.query.filter_by(slug=slug).first()
        if item is None:
            item = Settings(slug=slug, category=category)
            db.session.add(item)
            db.session.flush()
        for attr, value in kwargs.items():
            if value is not None:
                setattr(item, attr, value)
        db.session.commit()
