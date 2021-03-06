import json
from datetime import datetime
import sys
import os.path

from bearblog.extensions import db


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    slug = db.Column(db.String(100))
    _value = db.Column('value', db.Text)
    description = db.Column(db.Text)
    value_type = db.Column(db.String(40))
    category = db.Column(db.String(40))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    visibility = db.Column(db.String(40), default='visible')

    _default_categories = {}

    @property
    def value(self):
        return self.get_value_self()

    @value.setter
    def value(self, value):
        self._value = value

    @classmethod
    def get_setting(cls, slug, category=None):
        return Settings.query.filter_by(slug=slug).first()

    @staticmethod
    def get_value(slug, category='bearblog'):
        item = Settings.query.filter_by(slug=slug, category=category).first()
        if item is not None:
            return item.get_value_self()
        return None

    def get_value_self(self):
        if self.value_type is None:
            return self._value
        if self.value_type == 'str_list':
            return self._value.split()
        if self.value_type == 'signal':
            return json.loads(self._value)
        return eval(self.value_type)(self._value)

    @staticmethod
    def get(slug, category='settings'):
        item = Settings.query.filter_by(slug=slug, category=category).first()
        if item is None:
            return None
        return {
            'raw_value': item._value,
            'value': Settings.get_value(slug, category),
            'description': item.description,
            'value_type': item.value_type
        }

    @classmethod
    def set_setting(cls, slug, category=None, **kwargs):
        if category is None:
            frame = sys._getframe(1)
            caller_file = os.path.abspath(frame.f_code.co_filename)
            matches = [category for category in cls._default_categories if caller_file.startswith(category)]
            if matches:
                category = cls._default_categories[max(matches, key=len)]
        if category is None:
            category = 'settings'
        cls.set(slug, category, **kwargs)

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

    @classmethod
    def add_default_category(cls, path, category):
        cls._default_categories[path] = category

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'rawValue': self._value,
            'value': self.value,
            'description': self.description,
            'rawValueType': self.value_type,
            'category': self.category,
            'timestamp': self.timestamp,
            'visibility': self.visibility
        }
