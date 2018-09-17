from ... import db
from datetime import datetime


class CommentToMail(db.Model):
    __tablename__ = 'comment_to_mail'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    log = db.Column(db.Text)
    comment = db.relationship('Comment', backref='comment_to_mail')


class OAuth2Meta(db.Model):
    __tablename__ = 'comment_to_mail_oauth2_meta'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Text)
    value = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get(key):
        item = OAuth2Meta.query.filter_by(key=key).first()
        if item is not None:
            return item.value
        return None

    @staticmethod
    def set(key, value):
        item = OAuth2Meta.query.filter_by(key=key).first()
        if item is None:
            item = OAuth2Meta(key=key)
            db.session.add(item)
            db.session.flush()
        item.value = value
        db.session.commit()


class Message(db.Model):
    __tablename__ = 'comment_to_mail_messages'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    status = db.Column(db.Text)
    message_id = db.Column(db.Text)
    sent_date_time = db.Column(db.DateTime)
    recipient = db.Column(db.Text)
    web_link = db.Column(db.Text)

    comment = db.relationship('Comment', backref='message')
