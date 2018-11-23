from ... import db
from datetime import datetime


class Settings(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text)
    value = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get(key):
        item = Settings.query.filter_by(key=key).first()
        if item is not None:
            return item.value
        return None

    @staticmethod
    def set(key, value):
        item = Settings.query.filter_by(key=key).first()
        if item is None:
            item = Settings(key=key)
            db.session.add(item)
            db.session.flush()
        item.value = value
        db.session.commit()
