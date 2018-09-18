from .extensions import db, login_manager
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', back_populates='role', lazy='dynamic')

    @staticmethod
    def insert_roles():
        roles = ('管理员', '访客')
        default_role = '访客'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    @staticmethod
    def admin():
        return Role.query.filter_by(name='管理员').first()

    @staticmethod
    def guest():
        return Role.query.filter_by(name='访客').first()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    name = db.Column(db.String(64))
    email = db.Column(db.String(64))
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    role = db.relationship('Role', back_populates='users')

    @staticmethod
    def create(role, id=None, username=None, name=None, email=None, member_since=None, password=None, **kwargs):
        filter_kwargs = {}
        for param in ['id', 'username', 'name', 'email', 'member_since', 'password']:
            if eval(param) is not None:
                filter_kwargs[param] = eval(param)
        filter_kwargs['role'] = role
        return User(**filter_kwargs)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
