from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager

bootstrap = Bootstrap()
moment = Moment()
db = SQLAlchemy()
jwt = JWTManager()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
