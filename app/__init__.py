from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config
from flask_wtf.csrf import CSRFProtect
from flask_nav import Nav, register_renderer
from flask_moment import Moment

bootstrap = Bootstrap()
db = SQLAlchemy()
csrf = CSRFProtect()
nav = Nav()
moment = Moment()

login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    moment.init_app(app)

    from .plugins import load_plugins
    load_plugins()

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .main import custom_navbar as main_navbar, NavbarRenderer as main_NavbarRenderer
    register_renderer(app, 'main', main_NavbarRenderer)
    nav.register_element('main', main_navbar)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from . import jinja2_customs
    jinja2_customs.custom(app)

    nav.init_app(app)

    return app
