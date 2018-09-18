from flask import Flask
from config import config
import flask_whooshalchemyplus
from flask_whooshalchemyplus import index_all
from . import signals
from .extensions import bootstrap, db, login_manager, csrf, moment


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

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .admin import admin as admin_blueprint
    app.register_blueprint(admin_blueprint, url_prefix='/admin')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')

    from .plugins import plugin as plugin_blueprint
    app.register_blueprint(plugin_blueprint, url_prefix='/plugin')

    signals.init_app.send(app=app)

    from . import jinja2_customs
    jinja2_customs.custom(app)

    flask_whooshalchemyplus.init_app(app)

    return app
