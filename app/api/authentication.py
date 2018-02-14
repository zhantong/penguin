from flask_httpauth import HTTPBasicAuth
from . import api
from ..models import User
from flask import g
from .errors import unauthorized, forbidden

auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(username, password):
    if username == '':
        return False
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    g.current_user = user
    return True
    # return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')


@api.before_request
@auth.login_required
def before_request():
    if g.current_user.is_anonymous:
        return forbidden('Unconfirmed account')
