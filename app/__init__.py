from flask import Flask
from config import config
import flask_whooshalchemyplus
from flask_whooshalchemyplus import index_all
from .extensions import bootstrap, db, login_manager, csrf, moment
from .plugins.models import Plugin
import os
from app.extensions import db
from app.models import Role
import click
import json
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
import redis
from rq import Connection, Worker

current_plugin = Plugin('penguin', 'penguin', show_in_sidebar=False)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    register_extensions(app)

    from .plugins import load_plugins
    load_plugins()

    register_blueprints(app)
    register_commands(app)

    from . import jinja2_customs
    jinja2_customs.custom(app)

    Plugin.Signal.send('penguin', 'create_app', app=app)

    flask_whooshalchemyplus.init_app(app)

    return app


def register_blueprints(app):
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


def register_extensions(app):
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    moment.init_app(app)


def register_commands(app):
    @app.cli.command()
    def deploy():
        db.create_all()

        Role.insert_roles()

        current_plugin.signal.send_this('deploy')

    @app.cli.command()
    @click.option('--file-path', default=None, help='dumped file path')
    def restore(file_path):
        from migrations.Restore import Restore
        Restore(file_path).restore()

    @app.cli.command()
    def download_js_packages():
        def download_js_package(config_file_path):
            with open(config_file_path, 'r') as f:
                config = json.loads(f.read())
            for name, url in config.items():
                print(name, url)
                with urlopen(url) as resp:
                    with ZipFile(BytesIO(resp.read())) as zipfile:
                        zipfile.extractall(os.path.dirname(config_file_path))

        download_js_package(os.path.abspath('app/static/package.json'))

        for name in os.listdir('app/plugins/'):
            config_file_path = os.path.abspath(os.path.join('app', 'plugins', name, 'static', 'package.json'))
            if os.path.exists(config_file_path):
                download_js_package(config_file_path)

    @app.cli.command()
    def show_signals():
        import blinker
        import inspect
        signals = blinker.signal.__self__
        for name, signal in sorted(signals.items()):
            print(name)
            for func in signal.receivers.values():
                func_type = type(func)
                if func_type is blinker._utilities.annotatable_weakref:
                    func = func()
                print('\t', 'name: ', func.__name__, 'signature: ', inspect.signature(func), 'file: ', inspect.getsourcefile(func), 'line: ', func.__code__.co_firstlineno)

    @app.cli.command()
    def show_signals_new():
        signals = Plugin.Signal._signals
        for signal, value in signals.items():
            print(signal)
            for name, value in value.items():
                print('\t', name)
                for item in value:
                    print('\t', '\t', item)

    @app.cli.command()
    def run_worker():
        redis_url = app.config['REDIS_URL']
        redis_connection = redis.from_url(redis_url)
        with Connection(redis_connection):
            worker = Worker(app.config['QUEUES'])
            worker.work()
