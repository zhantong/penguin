from bearblog.extensions import db


class ViewCount(db.Model):
    __tablename__ = 'view_counts'
    id = db.Column(db.Integer, primary_key=True)
    repository_id = db.Column(db.String(36), unique=True)
    count = db.Column(db.Integer, default=0)
