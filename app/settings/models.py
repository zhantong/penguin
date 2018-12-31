from app import db
from datetime import datetime
import json


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
    visibility = db.Column(db.String(40), default='visible')

    @staticmethod
    def get_value(slug, category='penguin'):
        item = Settings.query.filter_by(slug=slug, category=category).first()
        if item is not None:
            return item.get_value_self()
        return None

    def get_value_self(self):
        if self.value_type is None:
            return self.value
        if self.value_type == 'str_list':
            return self.value.split()
        if self.value_type == 'signal':
            return json.loads(self.value)
        return eval(self.value_type)(self.value)

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
