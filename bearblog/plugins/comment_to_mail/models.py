from datetime import datetime

from bearblog.extensions import db


class CommentToMail(db.Model):
    __tablename__ = 'comment_to_mail'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_sent = db.Column(db.Boolean, default=False)
    log = db.Column(db.Text)
    comment = db.relationship('Comment', backref='comment_to_mail')


class Message(db.Model):
    __tablename__ = 'comment_to_mail_messages'
    id = db.Column(db.Integer, primary_key=True)
    comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    status = db.Column(db.Text)
    job_id = db.Column(db.String(255))
    message_id = db.Column(db.Text)
    sent_date_time = db.Column(db.DateTime)
    recipient = db.Column(db.Text)
    web_link = db.Column(db.Text)

    comment = db.relationship('Comment', backref='message')
